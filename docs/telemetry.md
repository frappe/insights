# Telemetry

One row per event the app sends to Pulse. This file is the only definition of an event's name and properties. `develop` and `version-3` emit what this table says, and the file is byte-identical on both branches. A backport that drops a hunk because the feature is missing marks the row here instead.

Analysis happens in Insights, connected to the Pulse site's database. Pulse stores one row per event with the properties as a JSON column, capped at 4096 bytes, 50 items per list, depth 5.

## Questions

Shipping events exist to answer these. An event that answers none of them is planned and does not ship until a question needs it.

| # | Question | Read from |
|---|---|---|
| 1 | Can the data store be the default sync path | `site_tables`: `charts_fit / (charts_total - charts_unknown)`, `tables_over_limit` |
| 2 | Is the SQL or script editor worth investing in | `site_queries.queries_*`, `query_failed.interface` |
| 3 | Which operations and expression functions carry most queries | `site_queries` |
| 4 | Are templates an entry point or a demo | `workbook_template_imported`, `site_profile.first_workbook_from_template` |
| 5 | Are dashboards consumed or only built | `site_profile.viewers_last_30d / authors_last_30d`, `dashboards_viewed_last_30d`, `public_view_windows_last_30d` |
| 6 | Where do new sites stop | funnel: `data_source_created`, `query_created`, `chart_created`, `dashboard_created`, `dashboard_chart_added`, `share_granted`, `dashboard_viewed` |
| 7 | Weekly active sites, as authors and as viewers | `workbook_opened`, `dashboard_viewed`, `site_profile` |
| 8 | Does behaviour change after a version upgrade | every event by `app_version` |
| 9 | What fails most, by version | `query_failed`, `data_source_tested`, `data_store_imported` |
| 10 | Does the data store fail where the live connection does not | `query_failed.data_store` |
| 11 | What share of active sites is each cohort, and how does retention differ | every event by `entry`, `site_profile` as denominator |
| 12 | How long after a site exists is Insights installed, and how long after that is the first dashboard | `site_profile` timeline, answerable from the first send |
| 13 | Which ERPNext doctypes do queries read most | `site_tables.queried_tables` |
| 14 | On ERPNext sites, is the site DB the only source | `site_profile.data_sources_*` |

## Rules

- Name: `<object>_<verb>`, past tense, snake_case. Variation goes in properties, never in the name.
- Property keys are flat: `operations_filter: 30`, not `operations: {filter: 30}`. Lists stay lists, at most 50 items.
- Property values that name a feature use the slug suffix from `docs/features.md`, underscores for hyphens.
- Low cardinality only: enums, booleans, counts, buckets. Never user text, titles, SQL, column names, emails or record ids.
- Names of tables and apps leave the site only when they are standard: an app Frappe publishes, which the app declares itself in its `app_publisher` hook, or a doctype with `custom = 0` that such an app ships. Everything else is counted, never named.
- Numbers on an event are buckets unless they are small counts: `rows_bucket: under_10k, 10k_to_100k, 100k_to_1m, over_1m`, `duration_bucket: under_1s, 1_to_5s, 5_to_30s, over_30s`. Counts under 100 may stay exact.
- Facts about the site are a daily scan from the scheduler, never a click and never on the query or import path. The scan reports history from `creation` timestamps and the core `View Log`, so the first send covers every existing site.
- Frontend sends through `frontend/src2/telemetry.ts`'s `useTelemetry().capture(event, props)`. Backend sends through `insights.telemetry.capture(event, **props)`. Both add the properties every event carries. Daily events pass `interval="1d"`, which keeps one row per user per day and ignores properties.
- Milestones and outcomes belong on the backend. The frontend sends only the five creation events.
- `error_kind` is a closed list mapped from exception classes in one function. Add a value when `other` passes a tenth of failures.
- A new event or property lands in this file in the same PR as the code.

## Properties on every event

| Property | Source | Value |
|---|---|---|
| `app_version` | backend default; frontend from `insights.api.get_site_info` | `insights.__version__` |
| `entry` | backend, derived daily and cached; frontend from `insights.api.get_site_info` | `erpnext_site` when ERPNext is installed, `saas_trial` when the site has a Frappe Cloud team and no ERPNext, else `self_hosted` |
| site, user, team, timestamp | Pulse client | automatic |

## Shipping

### Raw events

| Event | Fires when | Properties | Features |
|---|---|---|---|
| `workbook_created` | a workbook document is inserted, backend | `from_template: bool` | workbook.create |
| `workbook_template_imported` | a template is imported, backend | `template: slug`, `app: the app the template is for, named when Frappe publishes it` | templates.import |
| `workbook_library_opened` | the template library opens | | templates.library |
| `query_created` | a query is added | `interface: builder, sql, script` | query.interface-picker |
| `query_failed` | a run is refused or fails, backend | `interface`, `error_kind: syntax, unknown_column, permission, connection, timeout, refused, other`, `data_store: bool`, `source_type: as data_source_created.type, unknown when the query reads more than one source` | query.expression-validation, query.unknown-operation-refused, query.source-cycle-refused, query.native-sql-one-statement |
| `chart_created` | a chart is added | | charts.type-* |
| `dashboard_created` | a dashboard is added | | dashboard.create-add-chart |
| `dashboard_chart_added` | a chart lands on a dashboard | `via: selector, drag`, `count: int` | dashboard.create-add-chart, dashboard.chart-selector, dashboard.drag-chart-from-sidebar |
| `share_granted` | access is given, backend | `object: workbook, dashboard, chart, data_source, table`, `with: user, org, team, public`, `count: int` | permissions.share-workbook-user, permissions.share-workbook-org, permissions.share-dashboard, permissions.team-grant, shared.dashboard-link, shared.chart-link, templates.import |
| `data_source_created` | a source is saved, backend | `type: site_db or database_type lowercased: mariadb, postgresql, clickhouse, duckdb, sqlite, bigquery`, `ssl: bool` | data-source.connect-*, data-source.ssl |
| `data_source_tested` | a connection test returns, backend | `type`, `ok: bool`, `error_kind` | data-source.test-connection, data-source.connection-error-detail |
| `data_store_imported` | an import job ends, backend | `outcome: ok, failed`, `hit_row_limit: bool`, `rows_bucket`, `duration_bucket`, `resumed: bool` | data-store.import-table, data-store.import-row-limit, data-store.import-cursor, data-store.failed-import-notice |

### Daily events, `interval 1d`

| Event | Fires when | Properties | Features |
|---|---|---|---|
| `workbook_opened` | `track_view` on a workbook, backend | `via: list, recent, desk, link` | workbook.open-tabs, workbook.home-recent, workbook.open-in-desk, workbook.list |
| `dashboard_viewed` | `track_view` on a dashboard, backend | `surface: workbook, shared, dashboards` | dashboard.loads, shared.dashboard-link, shared.chart-on-public-dashboard, shared.read-once, shared.currency-for-guest |
| `workbook_template_used` | a workbook from a template is viewed, backend | `template: slug` | templates.open |

One row per user per day. Guests of public dashboards share one user, so their row is one per site per day; `site_profile.public_view_windows_last_30d` counts their five-minute windows, which is a floor on views and never the volume.

### Site scan, one scheduler job

Daily because the job is daily, not because of an interval: Pulse drops an event that arrives before the interval has elapsed, and a scheduler tick a second early would cost the site that day.

Three events so each stays under the 4096-byte cap. Every property is a flat key.

A site with telemetry off is asked nothing: building the events reads every data source's catalog, and that is load on a customer's own database for an event Pulse drops.

| Event | Properties | Features |
|---|---|---|
| `site_profile` | identity: `frappe_cloud: bool`, `apps: list of standard app names`, `custom_apps: int`, `site_age_days`. Timeline: `insights_installed_days_ago`, `first_data_source_days_ago`, `first_workbook_days_ago`, `first_dashboard_days_ago`, `last_query_run_days_ago`, `first_workbook_from_template: bool`. Footprint: `data_sources_site_db, data_sources_mariadb, data_sources_postgresql, data_sources_clickhouse, data_sources_duckdb, data_sources_file, data_sources_demo, data_sources_other: int`, `workbooks, queries, charts, dashboards, alerts: int`, `charts_<chart_type>: int` per type the backend's chart type list holds, any other type counted as `charts_other`, `dashboards_with_filters: int`. People: `users_with_access: enabled users holding an Insights role`, `authors_last_30d` from the execution log, `viewers_last_30d`, `dashboards_viewed_last_30d`, `public_view_windows_last_30d`: View Log rows by Guest on dashboards, one per dashboard per five-minute window, so a floor on views | workbook.list, dashboard.list, data-source.list, settings.users-list, templates.open |
| `site_queries` | `queries_builder, queries_sql, queries_script: int`, `queries_on_store: int`, `operations_<kind>: int` and `queries_with_<kind>: int` for source, select, remove, rename, cast, filter, join, union, mutate, summarize, order_by, limit, pivot_wider, window, custom, sql_column, `filter_<variant>: int` with the operator as the variant, symbols spelled eq, neq, gt, gte, lt, lte, and `expression` for a free-form filter, `join_<type>: int`, `agg_<name>: int`, `expression_count: int`, `expression_functions: list of the 50 most used names`. An operator, join type, aggregation or function the engine does not know is counted as `filter_other`, `join_other`, `agg_other` and left out of the names — `operations` is free-form JSON, so only a value from the engine's own list leaves the site | query.source-*, query.filter*, query.join*, query.union*, query.mutate*, query.summarize*, query.order-by, query.limit, query.pivot-wider, query.custom-operation, query.sql-column, query.expression-json, query.native-sql, query.script, query.data-store-toggle |
| `site_tables` | `queried_tables: list of standard doctypes, the 50 read by most queries`, `custom_tables_queried: int`, `store_enabled: bool`, `row_limit: int`, `tables_over_limit: list of standard doctypes`, `charts_total`, `charts_fit`, `charts_unknown`, `charts_without_tables`, `charts_on_store: int` | data-store.import-row-limit, settings.data-store-enable, data-source.table-stats |

A chart fits when every table its query reads has an estimated row count under the row limit. `charts_total` counts the charts that read a table, unknown ones included, so the rate is `charts_fit / (charts_total - charts_unknown)`; a chart with no query, or whose query reads no table, is judged by nothing and counts in `charts_without_tables`. A chart reading a table nobody estimated is `charts_unknown` and counts in neither `charts_fit` nor `tables_over_limit`, so a source that did not answer never reads as too big. A table on incremental sync is already on the store and counts as fitting. Row counts are catalog estimates, `information_schema.TABLES.TABLE_ROWS`, `pg_class.reltuples`, `system.tables.total_rows`, `duckdb_tables().estimated_size`, never a count query. The scan writes them to `Insights Table v3.estimated_row_count` and `estimated_on` for tables a query reads, skips a source that does not answer, and is the only writer of those fields.

## Planned

Same rules. Each waits for a question.

| Event | Fires when | Properties | Features |
|---|---|---|---|
| `workbook_saved` | a save succeeds | `queries, charts, dashboards: int`, `changed_items: int` | workbook.save |
| `workbook_edited` | an item-level edit outside a query, chart or dashboard body | `action: rename, add_item, remove_item, folder, reorder, duplicate, copy, paste, delete, lineage_opened`, `item_type: query, chart, dashboard, folder` | workbook.rename, workbook.add-items, workbook.remove-item, workbook.folders, workbook.reorder, workbook.duplicate, workbook.copy-paste, workbook.lineage, workbook.delete |
| `workbook_template_updated` | a template workbook takes an update | `template: slug`, `auto: bool` | templates.update, templates.auto-update-pristine |
| `query_shape` | a workbook save carries a query whose operations changed, backend; for co-occurrence inside one query | `interface`, `operations: list of kinds in order`, `filter_variants, join_types, aggregations: list`, `has_pivot, has_custom, has_sql_column: bool`, `expression_count: int`, `expression_functions: list`, `data_store: bool`, `source_type`, `site_db_tables: list of standard doctypes` | as `site_queries` |
| `query_operation_added` | a pipeline operation is added or edited | `operation`, `variant`, `via: panel, column_header, inline, expression` | query.source-*, query.select-columns*, query.reopen-operation, query.remove-column, query.rename-column, query.cast-column, query.filter*, query.join*, query.union*, query.mutate*, query.summarize*, query.order-by, query.limit, query.pivot-wider, query.custom-operation, query.sql-column |
| `query_operation_removed` | an operation is removed or the pipeline steps back | `operation`, `via: remove, step_back, undo` | query.remove-operation, query.step-back, query.undo-redo |
| `query_result_action` | a user acts on the result pane | `action: download, find, paginate, drill, raw_row, view_sql, copy, paste, duplicate, rename, conditional_format, refresh_stored, format_sql, schema_explorer, force_run, logs, alerts_open` | query.download-results, query.result-find, query.result-pagination, query.result-drill, query.result-raw-row, query.view-sql, query.copy-paste, query.duplicate, query.rename, query.conditional-formatting, query.refresh-stored-tables, query.native-sql-format, query.native-sql-schema-explorer, query.script-force-run, query.script-logs, query.alerts-open, query.execute, query.row-count, query.result-timing, query.result-cache |
| `chart_type_switched` | the type changes on an existing chart | `from, to: chart_type` | charts.switch-type-keeps-config |
| `chart_configured` | a config option is set or cleared | `chart_type`, `option: slug suffix`, `cleared: bool` | charts.query-picker, charts.title, charts.preview-table-grain, charts.x-axis through charts.heatmap-show-values |
| `chart_action` | a toolbar action | `chart_type`, `action: refresh, export_png, duplicate, reset_options, view_sql, copy, paste, expand, retry, reset_filters, sort, preview_table_sort` | charts.refresh, charts.export-png, charts.duplicate, charts.reset-options, charts.view-sql, charts.copy-paste, charts.expand, charts.retry, charts.reset-filters, charts.preview-table-sort |
| `chart_drilled` | a drill opens | `chart_type`, `kind: rows, segment, date_segment, number_card, breakdown, record_link, open_as_query`, `depth: int`, `additive: bool` | charts.drill-* |
| `chart_viewed` | a standalone shared or embedded chart loads, backend | `chart_type`, `embed: bool` | shared.chart-link, shared.copy-link-embed, charts.table-renders-outside-dashboard |
| `dashboard_edited` | a layout or item edit | `action: move, resize, compact, filter_add, filter_link, filter_default, filter_icon, text_block, remove_item, reset_layout, rename, edit_chart` | dashboard.move-resize, dashboard.compact-layout, dashboard.filter-add, dashboard.filter-links, dashboard.filter-default, dashboard.filter-icon, dashboard.text-block, dashboard.remove-item, dashboard.reset-layout, dashboard.rename, dashboard.edit-chart |
| `dashboard_filter_applied` | a viewer sets or clears a filter | `kind: date, text, number`, `via: filter, card` | dashboard.filter-values, dashboard.filter-clear, dashboard.card-filter, shared.filters-on-public-dashboard |
| `dashboard_action` | a viewer action that is not a filter | `action: refresh, export_png, favorite, unfavorite, card_find, drill, open_workbook` | dashboard.refresh, dashboard.export-png, dashboard.favorite, dashboard.card-find, dashboard.drill, dashboard.open-workbook |
| `share_revoked` | access is removed, backend | `object`, `with` | shared.revoke |
| `access_refused` | a permission check refuses a request, backend | `check: edit, source, table_row, download, chart_link, dashboard_hold, query_reference, seat, malformed, search`, `object` | permissions.viewer-cannot-edit, permissions.no-source-access-no-query, permissions.table-row-restriction, permissions.download-gated, permissions.chart-cannot-link-unreadable-query, permissions.dashboard-cannot-hold-unreadable-chart, permissions.query-reference-checked, permissions.authoring-needs-seat, permissions.malformed-request-refused |
| `data_source_file_uploaded` | a file becomes a table, backend | `rows_bucket`, `size_kb: int`, `format: csv, xlsx, parquet` | data-source.upload-file, data-source.upload-table-name |
| `data_source_browsed` | the source explorer is used | `action: table_list, table_preview, table_links, table_stats, update_tables, schema_picked` | data-source.list, data-source.table-list, data-source.table-preview, data-source.table-links, data-source.table-stats, data-source.update-tables, data-source.postgres-schema |
| `data_store_maintained` | cleanup or compaction runs, backend | `job: cleanup, compaction`, `tables_pruned: int`, `duration_bucket` | data-store.cleanup-prunes-stale, data-store.compaction |
| `alert_created` | an alert is saved the first time, backend | `channel: email, webhook, telegram` | alerts.create |
| `alert_edited` | condition, message, channel or enabled state changes | `field: condition, message, channel, enabled`, `channel` | alerts.condition, alerts.message, alerts.email, alerts.webhook, alerts.telegram, alerts.enable |
| `alert_run` | a scheduled or test run ends, backend | `test: bool`, `outcome: sent, not_triggered, failed`, `channel`, `error_kind` | alerts.test-send, alerts.failed-run-recorded, alerts.webhook-address-policy |
| `setting_changed` | a settings value is saved | `setting: week_start, fiscal_year_start, permissions, apply_user_permissions, allow_download, data_store, color_scheme, team, profile` | settings.week-start, settings.fiscal-year-start, settings.permissions-toggle, settings.apply-user-permissions, settings.allow-download, settings.data-store-enable, settings.color-scheme, settings.team-manage, settings.profile |
| `users_invited` | invites are sent, backend | `count: int` | settings.invite-users |
| `demo_data_loaded` | demo data setup finishes, backend | `ok: bool` | settings.demo-data |
| `notice_dismissed` | a banner is closed | `notice: demo, security_update` | settings.demo-banner-dismiss, settings.security-update-notice |

## version-3 only

Existing names. develop has no v2 code.

| Event | Fires when | Properties |
|---|---|---|
| `v2_migration_scanned` | the scan finishes, backend | `dashboards, ready, review, migrated: int` |
| `v2_migration_offered` | the nudge is shown, `interval 1d`, backend | `waiting: int`, `can_migrate: bool` |
| `v2_migration_page_opened` | the settings page opens | `from` |
| `v2_migration_dashboard_opened` | a scanned dashboard is opened | `verdict` |
| `v2_migration_opened_in_v3` | a migrated dashboard is opened in v3 | |
| `v2_migration_started` | a run begins, backend | `accepted, skipped: int`, `reasons: list` |
| `v2_migration_finished` | a run ends, backend | `queries, dropped_queries, items: int`, `query_kinds: list` |
| `v2_migration_failed` | a run raises, backend | `error` |
| `v2_migration_dismissed`, `v2_migration_restored` | the nudge is hidden or brought back, backend | `waiting: int` |

## Retired

Stop emitting when the replacement ships. Dashboards keyed on these read both names until the old series ends.

| Event | Replaced by |
|---|---|
| `dashboard_shared_with_user` | `share_granted {object: dashboard, with: user}` |
| `dashboard_set_public` | `share_granted {object: dashboard, with: public}` |

## Not tracked

Guarantees, not actions: `query.expression-cannot-*`, `shared.rows-are-the-publishers`, `shared.publish-needs-share`, `shared.public-methods-bounded`, `shared.old-name-resolves`, `permissions.request-body-not-trusted`, `permissions.admin-bypass`, `permissions.non-insights-user`, `permissions.site-user-permissions`, `permissions.import-without-access`, `permissions.viewer-sees-granted`, `permissions.chart-access-follows`, `permissions.team-off-open`, `permissions.search-respects-access`, `data-store.write-lock`, `data-store.division-by-zero`, `data-store.cleanup-keeps-unexplained`, `data-source.credentials-stay-with-admins`, `data-source.table-label-is-text`, `templates.shipped-are-valid`, `charts.every-type-covered`, `charts.style-change-no-rerun`, `charts.missing-slot-message`, `charts.table-loading`, `charts.rename-while-saving`, `workbook.read-only-shield`, `query.download-cell-is-data`, `dashboard.breakpoints`, `dashboard.cell-height-rule`, `dashboard.number-cell-per-reading`, `dashboard.preview-image`, `settings.translations`, `settings.login`, `settings.log-out`, every `upgrade.*` and `tooling.*` row.

Counted by the automatic `pageview`: `charts.preview`, `data-store.list`. Passive help, not a decision: `query.expression-help`, `query.native-sql-autocomplete`, `query.script-variables`, `permissions.share-user-lookup`, `query.filter-operators-by-type`.
