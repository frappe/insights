import base64
import hashlib
import json
import os

import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils.synchronization import filelock

from insights.decorators import insights_whitelist
from insights.utils import DocShare, deep_convert_dict_to_dict

MANIFEST_REQUIRED_KEYS = ["title", "description", "required_apps", "source_doctypes"]

# The hook apps point at their shipped-workbooks directory with. Insights
# declares it too (see hooks.py), so the bundled ERPNext templates ride the
# same contract.
TEMPLATES_HOOK = "insights_workbooks"


def get_installed_apps() -> set[str]:
    # narrow seam over frappe.get_installed_apps so tests can fake the app set
    # without patching the global that frappe's own insert hooks rely on
    return set(frappe.get_installed_apps())


def _app_title(app: str) -> str:
    """The app's display title (e.g. "ERPNext"), for attribution in the library.
    Falls back to the package name if the title can't be read — doing so imports
    the app, which a not-genuinely-installed app (e.g. one faked in a test) can't
    satisfy, and a broken app shouldn't take down the library."""
    try:
        return (frappe.get_hooks("app_title", app_name=app) or [app])[0]
    except Exception:
        return app


def _grouping_app(entry: dict) -> str:
    """The app a template belongs to, for library grouping. Its first required
    app when it declares one — an Insights-bundled ERPNext dashboard belongs
    under ERPNext, not Insights, because the shipping app is an implementation
    detail. Otherwise the app that ships it (a standalone app groups under
    itself). required_apps are all installed by the time a template is listed,
    so the title always resolves."""
    required = entry["manifest"].get("required_apps") or []
    return required[0] if required else entry["app"]


def _load_manifest(folder_path: str) -> dict:
    """Read and validate a manifest; raise if a required key is missing or the
    list fields are the wrong shape, so _discover_templates can skip it."""
    with open(os.path.join(folder_path, "manifest.json")) as f:
        manifest = json.load(f)
    for key in MANIFEST_REQUIRED_KEYS:
        if key not in manifest:
            raise ValueError(f"manifest is missing required key '{key}'")
    for key in ("required_apps", "source_doctypes"):
        if not isinstance(manifest[key], list):
            raise ValueError(f"manifest key '{key}' must be a list")
    return manifest


def _discover_templates() -> dict[str, dict]:
    """The site's template library, derived live from installed apps' hooks —
    installing an app adds its workbooks, uninstalling removes them, with no
    migrate step or registry doctype.

    Returns qualified-id -> {app, folder, path, manifest}. The id is
    "{app}/{folder}" so two apps can ship a "sales" template without colliding,
    and so imported-state lookup has a stable key. Ids travel as `name` over the
    API, per Frappe convention. Only enumerated ids are ever resolved to a path,
    which is what keeps path traversal out of the callers.

    A single app shipping a broken manifest is skipped with a log line rather
    than taking down the whole library."""
    registry: dict[str, dict] = {}
    # iterate genuinely-installed apps, NOT the get_installed_apps() seam: reading
    # an app's hooks imports its module, and tests fake apps into that seam that
    # aren't importable. The seam is only for required_apps filtering downstream.
    for app in sorted(frappe.get_installed_apps()):
        for rel_path in frappe.get_hooks(TEMPLATES_HOOK, app_name=app) or []:
            base = os.path.join(frappe.get_app_path(app), rel_path)
            if not os.path.isdir(base):
                continue
            for folder in sorted(os.listdir(base)):
                folder_path = os.path.join(base, folder)
                if not os.path.isfile(os.path.join(folder_path, "manifest.json")):
                    continue
                try:
                    manifest = _load_manifest(folder_path)
                except Exception:
                    frappe.log_error(
                        title="Invalid workbook template manifest",
                        message=f"Skipping template {app}/{folder}",
                    )
                    continue
                registry[f"{app}/{folder}"] = {
                    "app": app,
                    "folder": folder,
                    "path": folder_path,
                    "manifest": manifest,
                }
    return registry


def _resolve_template(template_name: str) -> dict:
    entry = _discover_templates().get(template_name)
    if not entry:
        frappe.throw(_("Workbook template {0} does not exist").format(frappe.bold(template_name)))
    return entry


def get_template_names() -> list[str]:
    return sorted(_discover_templates().keys())


def get_template_path(template_name: str) -> str:
    return _resolve_template(template_name)["path"]


def get_template_manifest(template_name: str) -> dict:
    return _resolve_template(template_name)["manifest"]


def get_template_workbook(template_name: str) -> dict:
    with open(os.path.join(get_template_path(template_name), "workbook.json")) as f:
        return json.load(f)


def get_template_preview(template_name: str) -> str | None:
    path = os.path.join(get_template_path(template_name), "preview.png")
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def has_required_apps(manifest: dict) -> bool:
    return set(manifest.get("required_apps") or []) <= get_installed_apps()


def has_source_data(manifest: dict) -> bool:
    """Cheap EXISTS across the template's source tables — True if any of them
    holds a row, so the UI can warn that the imported dashboards will be empty.
    Checking only the first table would miss data living in the others."""
    for doctype in manifest.get("source_doctypes") or []:
        if not frappe.db.table_exists(doctype):
            continue
        table = frappe.qb.DocType(doctype)
        if frappe.qb.from_(table).select(table.name).limit(1).run():
            return True
    return False


def get_imported_templates() -> dict[str, str]:
    """Map of template name -> the workbook the site already created from it.
    One shared copy per site (not per user), and derived from a live query (not a
    stored flag), so deleting the workbook re-enables its template on its own."""
    rows = frappe.get_all(
        "Insights Workbook",
        filters={"from_template": ["!=", ""]},
        fields=["from_template", "name"],
        order_by="creation asc",
    )
    # if a duplicate ever slips past the import lock, the oldest copy wins
    imported: dict[str, str] = {}
    for row in rows:
        imported.setdefault(row["from_template"], row["name"])
    return imported


@insights_whitelist()
def get_workbook_templates() -> list[dict]:
    """Every installed app's templates whose required_apps are also all
    installed. Empty on a site without the apps a template needs, so the library
    renders nothing there."""
    imported = get_imported_templates()
    templates = []
    for name, entry in sorted(_discover_templates().items()):
        manifest = entry["manifest"]
        if not has_required_apps(manifest):
            continue
        group_app = _grouping_app(entry)
        version = cint(manifest.get("version") or 1)
        imported_workbook = imported.get(name)
        # only the shipped version differing from the imported one is an update;
        # only then is it worth exporting the copy to check for local edits
        imported_version = (
            cint(frappe.db.get_value("Insights Workbook", imported_workbook, "imported_version"))
            if imported_workbook
            else None
        )
        update_available = bool(imported_workbook) and version > imported_version
        templates.append(
            {
                "name": name,
                "title": manifest.get("title") or name,
                "description": manifest.get("description"),
                "notes": manifest.get("notes"),
                "module": manifest.get("module"),
                # the app the template is for — its section in the library
                "app": group_app,
                "app_title": _app_title(group_app),
                # absent = v1; the key that makes "update available" possible
                "version": version,
                "has_data": has_source_data(manifest),
                "preview_image": get_template_preview(name),
                # workbook the site already imported from the template, else None
                "imported_workbook": imported_workbook,
                "imported_version": imported_version,
                "update_available": update_available,
                # whether taking the update would overwrite local edits — the
                # library warns before replacing a touched copy
                "customized": update_available and _is_customized(imported_workbook),
            }
        )
    return templates


def _find_imported_workbook(template_name: str) -> str | None:
    """The site's existing workbook for this template, if any (oldest wins)."""
    return frappe.db.get_value(
        "Insights Workbook",
        {"from_template": template_name},
        "name",
        order_by="creation asc",
    )


# child doctypes an imported workbook owns; kept in sync with InsightsWorkbook.on_trash
_WORKBOOK_CHILD_DOCTYPES = (
    "Insights Query v3",
    "Insights Chart v3",
    "Insights Dashboard v3",
    "Insights Folder",
)


def _reassign_to_administrator(workbook_name: str) -> None:
    """Own the imported workbook (and its children) as Administrator, so it's a
    shared org resource rather than tied to the admin who happened to click Import
    (and so only real admins can edit/delete it — everyone else reads via the share)."""
    frappe.db.set_value("Insights Workbook", workbook_name, "owner", "Administrator")
    for doctype in _WORKBOOK_CHILD_DOCTYPES:
        frappe.db.set_value(doctype, {"workbook": workbook_name}, "owner", "Administrator")


def _share_with_organization(workbook_name: str) -> None:
    """Implicit organization: view share — same shape update_share_permissions
    produces, so everyone with Insights access can read the shared copy."""
    share = DocShare.get_or_create_doc(
        share_doctype="Insights Workbook",
        share_name=workbook_name,
        everyone=1,
    )
    share.read = 1
    share.write = 0
    share.notify_by_email = 0
    # Creating the org-shared copy is a privileged system action; it must not
    # hinge on the acting admin's share right on the workbook (which they lose
    # once ownership moves to Administrator). ignore_permissions doesn't cover
    # DocShare's own share-permission check — ignore_share_permission does.
    share.flags.ignore_share_permission = True
    share.save(ignore_permissions=True)


def _template_import_result(workbook_name: str) -> dict:
    """Workbook + its first dashboard, so the client can land on the dashboard."""
    first_dashboard = frappe.db.get_value(
        "Insights Dashboard v3",
        {"workbook": workbook_name},
        "name",
        order_by="creation asc",
    )
    return {"workbook": workbook_name, "dashboard": first_dashboard}


@insights_whitelist(role="Insights Admin")
def create_workbook_from_template(template_name: str) -> dict:
    from insights.insights.doctype.insights_workbook.insights_workbook import import_workbook

    # resolve against the enumerated registry (never split+join the id onto a
    # path), so an unknown id — or a "../" traversal attempt — is thrown out here
    manifest = _resolve_template(template_name)["manifest"]
    if not has_required_apps(manifest):
        frappe.throw(
            _("Workbook template {0} requires apps that are not installed: {1}").format(
                frappe.bold(manifest.get("title") or template_name),
                ", ".join(manifest.get("required_apps") or []),
            )
        )

    # One shared copy per site. Serialize the check-then-insert so two admins
    # clicking simultaneously on a fresh site can't both create a copy. The id's
    # "/" is flattened so it stays a plain lock filename, not a nested path.
    lock_key = f"insights_template_import_{template_name.replace('/', '_')}"
    with filelock(lock_key, timeout=60):
        existing = _find_imported_workbook(template_name)
        if existing:
            return _template_import_result(existing)

        # Import as the caller (don't frappe.set_user mid-request — it rewrites the
        # session sid and logs the user out), then hand the copy to Administrator so
        # it becomes a shared org resource that everyone else reads via the share.
        workbook_name = import_workbook(get_template_workbook(template_name))
        # tag the origin so the library can mark this template as imported
        frappe.db.set_value("Insights Workbook", workbook_name, "from_template", template_name)
        _reassign_to_administrator(workbook_name)
        _share_with_organization(workbook_name)
        # record which shipped version this copy holds, and a fingerprint of it as
        # imported — the fingerprint is what later tells a pristine copy (safe to
        # auto-update) from one the site has edited (update only on request)
        _stamp_template_version(workbook_name, manifest)
        # Commit inside the lock so the copy is visible to the next admin who
        # takes it — the lock only serializes; without the commit the next holder
        # reads a pre-insert snapshot and creates a silent duplicate.
        frappe.db.commit()  # nosemgrep — intentional commit inside the import lock (see above)

    return _template_import_result(workbook_name)


def _workbook_checksum(workbook_name: str) -> str:
    """A content fingerprint of the workbook, stable across re-reads but sensitive
    to any edit of its queries/charts/dashboards. Compared against the value
    stored at import to tell whether the site has touched the shipped copy.
    `timestamp` is dropped because export() stamps it fresh every call."""
    payload = frappe.get_doc("Insights Workbook", workbook_name).export()
    payload.pop("timestamp", None)
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


def _is_customized(workbook_name: str) -> bool:
    """True if the copy has drifted from what was imported — or if we never
    recorded a fingerprint (a pre-versioning copy), which we treat as customized
    so it's never silently overwritten."""
    stored = frappe.db.get_value("Insights Workbook", workbook_name, "imported_checksum")
    return not stored or stored != _workbook_checksum(workbook_name)


def _stamp_template_version(workbook_name: str, manifest: dict) -> None:
    frappe.db.set_value(
        "Insights Workbook",
        workbook_name,
        {
            "imported_version": cint(manifest.get("version") or 1),
            "imported_checksum": _workbook_checksum(workbook_name),
        },
    )


def _replace_workbook_contents(workbook_name: str, workbook_json: dict) -> None:
    """Swap the workbook's contents for the template's, keeping the workbook's own
    name (so URLs and shares survive). Drops the existing children and rebuilds
    them from the shipped definition — safe on a pristine copy because there's
    nothing of the site's to lose."""
    workbook = deep_convert_dict_to_dict(frappe.parse_json(workbook_json))
    for doctype in _WORKBOOK_CHILD_DOCTYPES:
        for row in frappe.get_all(doctype, {"workbook": workbook_name}):
            frappe.delete_doc(doctype, row.name, force=True, ignore_permissions=True)

    doc = frappe.get_doc("Insights Workbook", workbook_name)
    new_title = (workbook.get("doc") or {}).get("title")
    if new_title:
        doc.db_set("title", new_title)
    doc.restore_workbook_contents(workbook, workbook_name, ignore_permissions=True)


def _update_imported_workbook(template_name: str, workbook_name: str) -> None:
    manifest = _resolve_template(template_name)["manifest"]
    _replace_workbook_contents(workbook_name, get_template_workbook(template_name))
    # rebuilt children default to the actor's ownership; hand them back to
    # Administrator so the shared-copy invariant from import still holds
    _reassign_to_administrator(workbook_name)
    _stamp_template_version(workbook_name, manifest)


@insights_whitelist(role="Insights Admin")
def update_workbook_from_template(template_name: str) -> dict:
    """Re-take the shipped version into the already-imported workbook, in place.
    The library offers this when a newer version ships; a customized copy is
    warned about client-side before the call, since this replaces its contents."""
    manifest = _resolve_template(template_name)["manifest"]
    if not has_required_apps(manifest):
        frappe.throw(
            _("Workbook template {0} requires apps that are not installed: {1}").format(
                frappe.bold(manifest.get("title") or template_name),
                ", ".join(manifest.get("required_apps") or []),
            )
        )

    workbook_name = _find_imported_workbook(template_name)
    if not workbook_name:
        return create_workbook_from_template(template_name)

    lock_key = f"insights_template_import_{template_name.replace('/', '_')}"
    with filelock(lock_key, timeout=60):
        _update_imported_workbook(template_name, workbook_name)
        # commit inside the lock so a concurrent caller sees the finished copy,
        # not a half-rebuilt one
        frappe.db.commit()  # nosemgrep — intentional commit inside the import lock

    return _template_import_result(workbook_name)


def sync_workbook_template_updates() -> None:
    """Run on migrate: carry a newer shipped version into pristine imported copies
    with no clicks (nothing of the site's to clobber). A copy the site has edited
    is left alone — the library surfaces a manual update for it instead."""
    registry = _discover_templates()
    # persist whatever earlier after_migrate steps left pending, so the per-copy
    # rollback below can only ever discard the copy it was updating
    frappe.db.commit()  # nosemgrep — flush prior after_migrate work before per-copy rollbacks
    for template_name, workbook_name in get_imported_templates().items():
        entry = registry.get(template_name)
        if not entry:
            continue
        version = cint(entry["manifest"].get("version") or 1)
        imported_version = cint(frappe.db.get_value("Insights Workbook", workbook_name, "imported_version"))
        try:
            if not imported_version:
                # a copy imported before versioning existed: adopt the current version
                # as its baseline (so it doesn't read as "update available"), but leave
                # its checksum empty so it counts as customized and is never auto-updated
                frappe.db.set_value("Insights Workbook", workbook_name, "imported_version", version)
            elif imported_version < version and not _is_customized(workbook_name):
                _update_imported_workbook(template_name, workbook_name)
            else:
                continue
            # commit per copy so each update is atomic — the delete-then-rebuild in
            # _update_imported_workbook either lands whole or, on failure below, is
            # rolled back, never left committed with the copy emptied
            frappe.db.commit()  # nosemgrep — land each copy atomically (paired with the rollback below)
        except Exception:
            frappe.db.rollback()
            frappe.log_error(title=f"Failed to sync workbook template {template_name}")
