// The form of a Dashboard Chart or Number Card that shows an Insights chart.
// Desk's own definition is hidden and not required: the island renders the
// document, and Insights fills the definition desk needs when it saves
// (`insights.desk.fill_desk_definition`). The form previews the chart instead.

frappe.provide("insights.desk");

const LAYOUT_FIELDTYPES = ["Section Break", "Column Break", "Tab Break"];

/**
 * The form events for `doctype`.
 *
 * `keep` lists the fields that still mean something for an Insights chart.
 * `props` are the island's props beside the chart. `chart_types` narrows the
 * picker to the charts that suit the doctype.
 */
insights.desk.chart_form = ({ keep, props, chart_types, height }) => {
	function show(frm) {
		const claimed = Boolean(frm.doc.insights_chart);
		// desk's own `before_save` parses the filters, and the form never set them
		if (claimed && !frm.doc.filters_json) frm.doc.filters_json = "[]";
		for (const df of frappe.get_meta(frm.doctype).fields) {
			if (
				keep.includes(df.fieldname) ||
				LAYOUT_FIELDTYPES.includes(df.fieldtype)
			)
				continue;
			frm.set_df_property(
				df.fieldname,
				"hidden",
				claimed ? 1 : df.hidden,
			);
			// before `reqd`: a field refresh sets `reqd` from `mandatory_depends_on`
			frm.set_df_property(
				df.fieldname,
				"mandatory_depends_on",
				claimed ? "" : df.mandatory_depends_on,
			);
			frm.set_df_property(df.fieldname, "reqd", claimed ? 0 : df.reqd);
		}
		preview(frm);
	}

	function preview(frm) {
		const chart = frm.doc.insights_chart;
		if (frm.insights_preview?.chart === chart) return;

		frm.insights_preview?.handle.unmount();
		frm.insights_preview?.$el.remove();
		frm.insights_preview = null;
		if (!chart || !frappe.ui.mount_island) return;

		const $el = $(`<div class="insights-chart-preview"></div>`)
			.css({
				height: `${height}px`,
				marginBottom: "var(--margin-md)",
				padding: "var(--padding-sm)",
				border: "1px solid var(--border-color)",
				borderRadius: "var(--border-radius-md)",
			})
			.insertAfter(frm.fields_dict.insights_chart.$wrapper);
		const handle = frappe.ui.mount_island("insights.chart", $el.get(0), {
			chart,
			...props,
		});
		frm.insights_preview = { chart, $el, handle };
	}

	return {
		setup(frm) {
			frm.set_query("insights_chart", () => ({
				filters: { chart_type: chart_types },
			}));
		},
		refresh: show,
		insights_chart: show,
	};
};
