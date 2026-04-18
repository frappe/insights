// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Insights Table v3", {
	refresh: function (frm) {
		frm.add_custom_button(__("Import to Warehouse"), function () {
			frm.call("import_to_warehouse").then(() => {
				frappe.msgprint(__("Import job has been queued"));
			});
		});

		if (frm.doc.stored) {
			frm.add_custom_button(__("Clear Warehouse Data"), function () {
				frappe.confirm(
					__(
						"This will delete all warehouse data for <b>{0}</b> and reset the sync bookmark. Are you sure?",
						[frm.doc.label || frm.doc.table],
					),
					() => {
						frm.call("clear_warehouse_data").then(() => {
							frappe.show_alert({
								message: __("Warehouse data cleared"),
								indicator: "green",
							});
							frm.reload_doc();
						});
					},
				);
			});
		}

		frm.add_custom_button(__("Statistics"), function () {
			frm.call("get_stats").then((r) => {
				const s = r.message;
				if (!s) return;

				const fmt_dt = (val) =>
					val ? frappe.datetime.str_to_user(val) : "—";
				const fmt_dur = (sec) => (sec ? `${sec}s` : "—");
				const fmt_num = (n) => (n != null ? String(n) : "—");

				const queries_html =
					s.referencing_queries && s.referencing_queries.length
						? s.referencing_queries
								.map(
									(q) =>
										`<li><a href="/app/insights-query-v3/${
											q.name
										}">${frappe.utils.escape_html(
											q.title || q.name,
										)}</a></li>`,
								)
								.join("")
						: "<li>—</li>";

				const html = `
<div style="font-size:13px;line-height:2">
  <h5 style="line-height: 24px; margin-bottom: 0px;">${__("Sync")}</h5>
  <table class="table table-condensed table-bordered" style="margin-top: 8px;">
    <tr><td>${__("Last Synced On")}</td><td>${fmt_dt(
		s.last_synced_on,
	)}</td></tr>
    <tr><td>${__("Last Import Rows")}</td><td>${fmt_num(
		s.last_import_rows,
	)}</td></tr>
    <tr><td>${__("Last Import Duration")}</td><td>${fmt_dur(
		s.last_import_duration,
	)}</td></tr>
    <tr><td>${__("Total Syncs")}</td><td>${fmt_num(s.total_syncs)}</td></tr>
    <tr><td>${__("Total Sync Time")}</td><td>${fmt_dur(
		s.total_sync_time,
	)}</td></tr>
    <tr><td>${__("Failed Syncs")}</td><td>${fmt_num(s.failed_syncs)}</td></tr>
  </table>
  <h5 style="line-height: 24px; margin-bottom: 0px;">${__("Usage")}</h5>
  <table class="table table-condensed table-bordered" style="margin-top: 8px;">
    <tr><td>${__("Last Executed On")}</td><td>${fmt_dt(
		s.last_executed_on,
	)}</td></tr>
    <tr><td>${__("Execution Count")}</td><td>${fmt_num(
		s.execution_count,
	)}</td></tr>
  </table>
  <h5 style="line-height: 24px; margin-bottom: 0px;">${__(
		"Referencing Queries",
  )}</h5>
  <ul style="padding-left:18px;margin:0">${queries_html}</ul>
</div>`;

				new frappe.ui.Dialog({
					title: __("Statistics — {0}", [
						frm.doc.label || frm.doc.table,
					]),
					fields: [{ fieldtype: "HTML", options: html }],
					primary_action_label: __("Close"),
					primary_action(values) {
						this.hide();
					},
				}).show();
			});
		});
	},
});
