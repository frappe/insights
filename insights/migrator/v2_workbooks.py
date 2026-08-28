"""Assemble one v2 dashboard into one v3 workbook.

The four translators know how to convert a thing. This module decides *what* to
convert, in what order, and writes it. The migration unit is a dashboard's
dependency closure, because a v2 query reached only through a Query Store
reference is as necessary as one a chart names directly.

The module has two halves, and the seam between them is the point:

- `plan_dashboard` is pure. Rows in, a `DashboardPlan` out, no database. It
  resolves the closure, orders it, runs the four translators and collects every
  gap. A dry run over an export is the same call the write path makes.
- `migrate_dashboard` reads v2, plans, and writes v3 inside a savepoint. It
  never writes to a v2 table.

The v2 side is read by SQL, and deliberately does not depend on the ORM. A v2
doctype is removed code: when the removal patch runs, its `tabDocType` and
`tabDocField` rows go with it, while `tabInsights Query` and every row in it
stay. The site that most needs a migrator is the one that has already dropped
the v2 app code, so the read path is written to need no v2 meta at all. Where
the meta is still present the ORM would work too - it is just not relied on.

Four things the v3 side decides, which the plan only records:

- **Data sources do not share names.** A v2 `Insights Data Source` is named by
  its title verbatim ("frappe.io"); a v3 `Insights Data Source v3` is named
  `frappe.scrub(title)` ("frappe_io"). Nothing correlates the two, so
  `resolve_v3_data_source` matches by name, then by scrubbed name, then by
  title, and reports a miss. The migrator never creates a data source: it holds
  no credentials, and a v2 password is encrypted against a different doctype.
- **v2 always read the live source**, so every migrated query does too.
  `TranslatedQuery.use_live_connection` is only set by the SQL floor; a builder
  query left at the default would read the DuckDB store instead, which holds
  different rows or none.
- **A chart's `data_query` is the doctype's.** `set_data_query` creates it in
  `before_save`. Creating one here would leave an orphan.
- **`is_public` does not travel.** In v3, publishing grants the publisher's own
  read access to anyone with the link, and records that publisher in
  `permission_user`. Deriving a publisher from a v2 row would hand out an access
  nobody granted, so a public v2 dashboard lands private and is reported.

Re-running is a skip. `old_name` carries the v2 docname on all three v3
doctypes, so a second run finds the dashboard it already made and returns it
untouched. A user who runs the migrator twice by accident gets neither a
duplicate workbook nor their post-migration edits overwritten.
"""

from dataclasses import dataclass, field

import frappe

from insights.migrator.v2_charts import (
    Gap,
    chart_from_dashboard_item,
    parse_json,
)
from insights.migrator.v2_dashboards import (
    FILTER_ITEM,
    TEXT_ITEM,
    TranslatedDashboard,
    translate_dashboard,
)
from insights.migrator.v2_queries import TranslatedQuery, translate_query

V2_DASHBOARD = "Insights Dashboard"
V2_DASHBOARD_ITEM = "Insights Dashboard Item"
V2_QUERY = "Insights Query"

V2_TRANSFORM = "Insights Query Transform"

V3_WORKBOOK = "Insights Workbook"
V3_DATA_SOURCE = "Insights Data Source v3"
V3_QUERY = "Insights Query v3"
V3_CHART = "Insights Chart v3"
V3_DASHBOARD = "Insights Dashboard v3"

KINDS = ("builder", "sql", "code", "none")


class CircularQueryReference(Exception):
    """A v2 closure whose references form a cycle.

    `Insights Query v3._validate_no_circular_dependency` rejects one at save, by
    which point half the workbook is written. This is raised before any write.
    """


# -- the plan ---------------------------------------------------------------


@dataclass
class QueryPlan:
    """One v2 query, translated, and where its data source landed."""

    source: str
    translated: TranslatedQuery
    data_source: str | None = None
    """The v3 data source name, or None when no v3 source answers to the v2 one."""

    @property
    def kind(self) -> str:
        return self.translated.kind

    @property
    def title(self) -> str:
        return self.translated.title

    @property
    def named_data_sources(self) -> set[str]:
        """The v2 data sources this query's operations actually name.

        Not the same as `translated.data_source`: a query whose source is
        another query names none, and "Query Store" is a v2 pseudo source that
        has no v3 counterpart by design.
        """
        named = set()
        for operation in self.translated.operations:
            for holder in (operation, operation.get("table") or {}):
                if holder.get("data_source"):
                    named.add(holder["data_source"])
        return named


@dataclass
class DashboardPlan:
    """Everything a migration will write, decided without touching the database.

    `queries` is in insert order: a query never comes before one it references.
    """

    source: str
    title: str
    queries: list[QueryPlan] = field(default_factory=list)
    dashboard: TranslatedDashboard | None = None
    gaps: list[Gap] = field(default_factory=list)
    columns_by_query: dict = field(default_factory=dict)
    data_source_map: dict = field(default_factory=dict)
    """Every v2 data source the operations name, mapped to a v3 one or to None."""

    item_count: int = 0

    @property
    def query_plans(self) -> dict[str, QueryPlan]:
        return {plan.source: plan for plan in self.queries}

    @property
    def kinds(self) -> dict[str, int]:
        counts = dict.fromkeys(KINDS, 0)
        for plan in self.queries:
            counts[plan.kind] = counts.get(plan.kind, 0) + 1
        return counts

    @property
    def dropped_queries(self) -> list[str]:
        """Queries that produced no operations at all."""
        return [plan.source for plan in self.queries if plan.kind == "none"]

    @property
    def converted_items(self) -> int:
        return len(self.dashboard.items) if self.dashboard else 0

    @property
    def dropped_items(self) -> int:
        return self.item_count - self.converted_items

    @property
    def unresolved_data_sources(self) -> list[str]:
        return sorted(name for name, resolved in self.data_source_map.items() if not resolved)

    @property
    def converts_cleanly(self) -> bool:
        """No item and no query was lost. A named downgrade does not count."""
        return not self.dropped_items and not self.dropped_queries and not self.blocking_gaps

    @property
    def blocking_gaps(self) -> list[Gap]:
        """Gaps the plan itself raised that stop a faithful migration."""
        return [gap for gap in self.gaps if gap.dropped]

    def all_gaps(self) -> list[tuple[str, Gap]]:
        """Every gap from every translator, tagged with where it came from."""
        reported = [("dashboard", gap) for gap in self.gaps]
        for plan in self.queries:
            reported += [(f"query {plan.source}", gap) for gap in plan.translated.gaps]
        if self.dashboard:
            reported += [("item", gap) for gap in self.dashboard.gaps]
        return reported


# -- closure ----------------------------------------------------------------


def source_tables(query: dict) -> list[str]:
    """Every table name a v2 query spec reads, in the order v2 names them.

    The source table and either side of a join. `v2_queries.table_ref` reads the
    same two places, so this cannot miss a table the translation would resolve.
    """
    spec = parse_json(query.get("json"))
    if not isinstance(spec, dict):
        return []

    names = []
    table = (spec.get("table") or {}).get("table")
    if table:
        names.append(table)

    for join in spec.get("joins") or []:
        for side in ("left_table", "right_table"):
            name = (join.get(side) or {}).get("table")
            if name and name not in names:
                names.append(name)

    return names


def direct_references(query: dict, known) -> list[str]:
    """The tables that are really other v2 queries - a Query Store reference."""
    return [name for name in source_tables(query) if name in known]


def closure(roots, queries: dict) -> list[str]:
    """The roots and everything they reach, each one after what it references.

    `Insights Query v3` rejects a cycle at save, so a cycle has to stop the
    migration before the first write, not after the last one.
    """
    known = queries.keys()
    deps: dict[str, list[str]] = {}
    pending = [name for name in roots if name in known]
    while pending:
        name = pending.pop()
        if name in deps:
            continue
        deps[name] = direct_references(queries[name], known)
        pending.extend(deps[name])

    ordered: list[str] = []
    placed: set[str] = set()
    while len(placed) < len(deps):
        ready = [name for name, refs in deps.items() if name not in placed and set(refs) <= placed]
        if not ready:
            unplaced = sorted(name for name in deps if name not in placed)
            raise CircularQueryReference(f"circular query reference among {', '.join(unplaced)}")
        ordered.extend(sorted(ready))
        placed.update(ready)

    return ordered


def result_columns(query: dict) -> list[dict]:
    """The columns a v2 query returned, read off its stored spec.

    A chart names its columns by the label v2 gave them, and `_Builder` keeps
    that label as the v3 dimension or measure name, so the two line up. This is
    what a dry run has instead of executing the query.
    """
    spec = parse_json(query.get("json"))
    if not isinstance(spec, dict):
        return []

    columns = []
    for column in spec.get("columns") or []:
        name = column.get("alias") or column.get("label") or column.get("column")
        if not name:
            continue
        columns.append({"name": name, "type": column.get("type") or "String"})
    return columns


def dashboard_roots(items: list[dict], queries: dict) -> tuple[list[str], list[dict]]:
    """The queries a dashboard's items name, and the items that name none.

    Only 162 of 1103 production items fill the `query` column; the rest keep it
    in `options`. `chart_from_dashboard_item` reads both, so it is the one
    reader here too.
    """
    roots: list[str] = []
    orphans: list[dict] = []
    for item in items:
        if item.get("item_type") in (TEXT_ITEM, FILTER_ITEM):
            continue
        query = chart_from_dashboard_item(item).get("query")
        if not query or query not in queries:
            orphans.append(item)
            continue
        if query not in roots:
            roots.append(query)
    return roots, orphans


def candidate_roots(items: list[dict]) -> list[str]:
    """Every query name the items mention, before anything says which exist."""
    names = []
    for item in items:
        if item.get("item_type") in (TEXT_ITEM, FILTER_ITEM):
            continue
        query = chart_from_dashboard_item(item).get("query")
        if query and query not in names:
            names.append(query)
    return names


# -- planning ---------------------------------------------------------------


def plan_dashboard(
    dashboard: dict,
    items: list[dict],
    queries: dict,
    *,
    resolve_data_source=None,
) -> DashboardPlan:
    """Decide the whole migration of one v2 dashboard. Pure: no database.

    `queries` maps a v2 query docname to its row, and needs to hold the closure
    - the whole v2 query index is the usual argument. `resolve_data_source`
    turns a v2 data source name into a v3 one, or None when there is no match;
    it defaults to assuming the name carries over, which is what a dry run over
    an export can check.
    """
    resolve_data_source = resolve_data_source or (lambda name: name)

    plan = DashboardPlan(
        source=dashboard.get("name") or "",
        title=dashboard.get("title") or dashboard.get("name") or "",
        item_count=len(items),
    )

    if dashboard.get("is_public"):
        plan.gaps.append(
            Gap(
                kind="public_not_carried",
                source=plan.source,
                detail="the v2 dashboard was public. v3 publishes by recording the "
                "publisher whose read access the link grants, so the migrated "
                "dashboard is private until someone publishes it",
            )
        )

    roots, orphans = dashboard_roots(items, queries)
    for item in orphans:
        plan.gaps.append(
            Gap(
                kind="item_without_query",
                source=str(item.get("name") or item.get("item_id") or ""),
                detail=f"a {item.get('item_type') or 'chart'} item names no v2 query that exists",
                dropped=True,
            )
        )

    try:
        ordered = closure(roots, queries)
    except CircularQueryReference as error:
        plan.gaps.append(
            Gap(
                kind="circular_query_reference",
                source=plan.source,
                detail=str(error),
                dropped=True,
            )
        )
        return plan

    # Every reference is spelled with its v2 name here, and bound to the v3 name
    # at write time. Naming the closure is what tells `translate_query` that a
    # table name is a query rather than a table.
    identity = {name: name for name in ordered}

    for name in ordered:
        row = queries[name]
        translated = translate_query(row, query_map=identity, workbook="")
        query_plan = QueryPlan(source=name, translated=translated)
        for v2_source in query_plan.named_data_sources:
            if v2_source not in plan.data_source_map:
                plan.data_source_map[v2_source] = resolve_data_source(v2_source)
        query_plan.data_source = plan.data_source_map.get(translated.data_source)
        plan.queries.append(query_plan)
        plan.columns_by_query[name] = result_columns(row)

    for v2_name in plan.unresolved_data_sources:
        plan.gaps.append(
            Gap(
                kind="unresolved_data_source",
                source=v2_name,
                detail=f"no Insights Data Source v3 answers to the v2 data source "
                f"{v2_name!r}. The queries migrate, and start working once a v3 "
                f"data source of that name exists",
                dropped=True,
            )
        )

    plan.dashboard = translate_dashboard(dashboard, items, columns_by_query=plan.columns_by_query)
    return plan


# -- reading v2 -------------------------------------------------------------


def load_v2_dashboard(name: str) -> tuple[dict, list[dict]]:
    """Read one v2 dashboard and its items. Read-only, and by SQL on purpose.

    The v2 meta is not depended on. Removing the v2 doctype takes its
    `tabDocType` row with it and leaves `tabInsights Dashboard` and its rows
    standing, so a site with the v2 code already gone still has everything this
    needs - as long as nothing here asks the meta.

    `SELECT *` for a different reason: `refactor_dashboard_item` moved
    `query`, `chart`, `markdown` and the filter fields into `options`, and the
    physical schema differs by how old the site is. Naming a column would fail
    on the site that dropped it and lose the rows that only fill it.
    """
    rows = _select(V2_DASHBOARD, "where name = %(name)s", {"name": name})
    if not rows:
        frappe.throw(frappe._("Dashboard {0} not found").format(name))

    items = _select(
        V2_DASHBOARD_ITEM,
        "where parent = %(name)s and parenttype = %(parenttype)s order by idx asc",
        {"name": name, "parenttype": V2_DASHBOARD},
    )
    return rows[0], items


def load_v2_queries(roots) -> dict:
    """The named v2 queries and everything they reference, by SQL.

    A closure is a median of 6 queries against a table of 2117, so this walks
    the graph outwards rather than reading the whole table. A table name is a
    query when a row answers to it, which is the one question the database has
    to settle: nothing in the spec marks a Query Store table as such.
    """
    queries: dict[str, dict] = {}
    frontier = {name for name in roots if name}

    while frontier:
        rows = _select(V2_QUERY, "where name in %(names)s", {"names": tuple(frontier)})
        if not rows:
            break
        for row in rows:
            queries[row["name"]] = row

        candidates = {table for row in rows for table in source_tables(row) if table not in queries}
        frontier = _existing_queries(candidates)

    if queries:
        for row in _select(
            V2_TRANSFORM,
            "where parenttype = %(parenttype)s and parent in %(names)s order by idx asc",
            {"parenttype": V2_QUERY, "names": tuple(queries)},
        ):
            queries[row["parent"]].setdefault("transforms", []).append(row)

    return queries


def _select(doctype: str, clause: str, values: dict) -> list[dict]:
    return frappe.db.sql(f"select * from `tab{doctype}` {clause}", values, as_dict=True)


def _existing_queries(names) -> set[str]:
    if not names:
        return set()
    rows = frappe.db.sql(
        f"select name from `tab{V2_QUERY}` where name in %(names)s",
        {"names": tuple(names)},
    )
    return {row[0] for row in rows}


def resolve_v3_data_source(v2_name: str) -> str | None:
    """The v3 data source a v2 one corresponds to, or None.

    v2 names a data source by its title verbatim, v3 by `frappe.scrub` of it, so
    the two only coincide for a title that was already scrubbed. Three lookups,
    widest last: the name as given, the scrubbed name, and any v3 source whose
    title is the v2 name.
    """
    if not v2_name:
        return None

    if frappe.db.exists(V3_DATA_SOURCE, v2_name):
        return v2_name

    scrubbed = frappe.scrub(v2_name)
    if frappe.db.exists(V3_DATA_SOURCE, scrubbed):
        return scrubbed

    return frappe.db.get_value(V3_DATA_SOURCE, {"title": v2_name}, "name")


# -- writing v3 -------------------------------------------------------------


@dataclass
class MigrationResult:
    """What the migration made, and what it could not carry.

    `query_names` is the seam the result-diff check is built on: it names the v3
    query that has to return what each v2 query returned.
    """

    plan: DashboardPlan
    workbook: str | None = None
    dashboard: str | None = None
    query_names: dict = field(default_factory=dict)
    chart_names: dict = field(default_factory=dict)
    skipped: bool = False

    @property
    def report(self) -> str:
        return format_report(self.plan, self)


def already_migrated(v2_dashboard: str) -> str | None:
    """The v3 dashboard a previous run made for this v2 one."""
    return frappe.db.get_value(V3_DASHBOARD, {"old_name": v2_dashboard}, "name")


def migrate_dashboard(name: str, *, owner: str | None = None) -> MigrationResult:
    """Copy one v2 dashboard into a new v3 workbook.

    Nothing in v2 is read for anything but reading. The whole write runs in a
    savepoint, so a failure anywhere leaves no workbook at all rather than half
    of one - `Insights Workbook.on_trash` would be the alternative, and it backs
    up and deletes, which is a lot of machinery for a state that need not exist.

    A dashboard already migrated is returned as it is. The plan is still built,
    so the caller gets the same report either way.
    """
    dashboard, items = load_v2_dashboard(name)
    queries = load_v2_queries(candidate_roots(items))
    plan = plan_dashboard(dashboard, items, queries, resolve_data_source=resolve_v3_data_source)

    existing = already_migrated(name)
    if existing:
        return MigrationResult(
            plan=plan,
            workbook=frappe.db.get_value(V3_DASHBOARD, existing, "workbook"),
            dashboard=existing,
            skipped=True,
        )

    owner = owner or dashboard.get("owner") or frappe.session.user

    frappe.db.savepoint("insights_v2_migration")
    try:
        return _write(plan, items, owner)
    except Exception:
        frappe.db.rollback(save_point="insights_v2_migration")
        raise


def _write(plan: DashboardPlan, items: list[dict], owner: str) -> MigrationResult:
    workbook = frappe.new_doc(V3_WORKBOOK)
    workbook.title = plan.title
    workbook.owner = owner
    workbook.insert(ignore_permissions=True)

    result = MigrationResult(plan=plan, workbook=workbook.name)

    for order, query_plan in enumerate(plan.queries):
        query = frappe.new_doc(V3_QUERY)
        query.workbook = workbook.name
        query.title = query_plan.title
        query.old_name = query_plan.source
        query.owner = owner
        query.sort_order = order
        query.operations = _bind_operations(query_plan, plan, result.query_names, workbook.name)
        # v2 read the live source, always. A builder query left at the default
        # would read the data store, which holds other rows or none.
        query.use_live_connection = query_plan.kind in ("builder", "sql")
        query.is_builder_query = query_plan.kind == "builder"
        query.is_native_query = query_plan.kind == "sql"
        query.is_script_query = query_plan.kind == "code"
        query.insert(ignore_permissions=True)
        result.query_names[query_plan.source] = query.name

    for order, chart in enumerate(plan.dashboard.charts):
        if not chart.chart_type:
            continue
        doc = frappe.new_doc(V3_CHART)
        doc.workbook = workbook.name
        doc.title = chart.title
        doc.old_name = chart.source
        doc.owner = owner
        doc.sort_order = order
        doc.chart_type = chart.chart_type
        doc.config = chart.config
        doc.query = result.query_names.get(chart.query)
        # `data_query` is left alone: `set_data_query` makes it in before_save.
        doc.insert(ignore_permissions=True)
        result.chart_names[chart.source] = doc.name

    # The second pass is the same pure call with the v3 names in hand. Items,
    # filter links and chart references all point at real rows from the start.
    bound = translate_dashboard(
        {"name": plan.source, "title": plan.title},
        items,
        chart_names=result.chart_names,
        query_names=result.query_names,
        columns_by_query=plan.columns_by_query,
    )

    dashboard = frappe.new_doc(V3_DASHBOARD)
    dashboard.workbook = workbook.name
    dashboard.title = plan.title
    dashboard.old_name = plan.source
    dashboard.owner = owner
    # `is_public` is deliberately not carried - see the module docstring.
    dashboard.items = bound.items
    dashboard.insert(ignore_permissions=True)
    result.dashboard = dashboard.name

    return result


def _bind_operations(query_plan: QueryPlan, plan: DashboardPlan, query_names: dict, workbook: str) -> list:
    """Point a planned query's operations at the rows they will actually read.

    The plan spells a reference and a data source with their v2 names. Both are
    rewritten here, where the v3 names exist. A reference always resolves,
    because the queries are inserted in closure order. A data source that
    resolved to nothing is left as it was: the name is then wrong in the same
    way the report says it is, and it starts working the moment a v3 data source
    of that name exists.
    """
    operations = frappe.parse_json(frappe.as_json(query_plan.translated.operations)) or []

    def rebind(holder):
        v2_source = holder.get("data_source")
        if v2_source:
            holder["data_source"] = plan.data_source_map.get(v2_source) or v2_source

    for operation in operations:
        rebind(operation)

        table = operation.get("table") or {}
        if table.get("type") == "query":
            table["query_name"] = query_names.get(table.get("query_name"), table.get("query_name"))
            table["workbook"] = workbook
        else:
            rebind(table)

    return operations


# -- reporting --------------------------------------------------------------


def format_report(plan: DashboardPlan, result: MigrationResult | None = None) -> str:
    """One dashboard's migration, as something a human reads top to bottom."""
    kinds = plan.kinds
    lines = [
        f"{plan.source} - {plan.title}",
        f"  queries: {len(plan.queries)} "
        f"(builder {kinds['builder']}, sql {kinds['sql']}, code {kinds['code']}, "
        f"nothing {kinds['none']})",
        f"  items: {plan.converted_items} of {plan.item_count} converted",
    ]

    if result and result.skipped:
        lines.append(f"  already migrated: dashboard {result.dashboard} in workbook {result.workbook}")
    elif result and result.workbook:
        lines.append(f"  workbook {result.workbook}, dashboard {result.dashboard}")

    if plan.dropped_queries:
        lines.append(f"  dropped queries: {', '.join(plan.dropped_queries)}")
    if plan.unresolved_data_sources:
        lines.append(f"  unresolved data sources: {', '.join(plan.unresolved_data_sources)}")

    gaps = plan.all_gaps()
    if not gaps:
        lines.append("  no gaps")
        return "\n".join(lines)

    lines.append("  gaps:")
    for origin, gap in gaps:
        mark = "!" if gap.dropped else "-"
        lines.append(f"    {mark} [{origin}] {gap.kind} ({gap.source}): {gap.detail}")

    return "\n".join(lines)
