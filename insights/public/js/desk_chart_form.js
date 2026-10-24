// The form of a Dashboard Chart or Number Card that shows an Insights chart.
// Desk's own definition is hidden and not required: the island renders the
// document, and Insights fills the definition desk needs when it saves
// (`insights.desk.fill_desk_definition`). The form previews the chart instead.

frappe.provide("insights.desk");

const LAYOUT_FIELDTYPES = ["Section Break", "Column Break", "Tab Break"];

/**
 * The form events for `doctype`.
 *
 * `keep` lists the fields that still mean something for an Insights chart, and
 * `label_field` is the one of them that names the document. `props` are the
 * island's props beside the chart. `chart_types` narrows the picker to the
 * charts that suit the doctype.
 */
insights.desk.chart_form = ({
	keep,
	label_field,
	props,
	chart_types,
	height,
}) => {
	// Desk's own wording is about desk's permissions. For an Insights chart,
	// Is Public only lists it in other users' pickers, and the Insights chart's
	// sharing decides who sees it.
	const CLAIMED_FIELDS = {
		is_public: {
			label: __("Others can add it to their dashboards"),
			description: __(
				"Lists it when other users add a chart to a dashboard or workspace. It does not change who sees it.",
			),
		},
		// only a developer exports standard documents
		is_standard: { hidden: frappe.boot.developer_mode ? 0 : 1 },
	};

	function show(frm) {
		const claimed = Boolean(frm.doc.insights_chart);
		// desk's own `before_save` parses the filters, and the form never set them
		if (claimed && !frm.doc.filters_json) frm.doc.filters_json = "[]";
		for (const df of frappe.get_meta(frm.doctype).fields) {
			if (CLAIMED_FIELDS[df.fieldname]) {
				for (const [property, value] of Object.entries(
					CLAIMED_FIELDS[df.fieldname],
				))
					frm.set_df_property(
						df.fieldname,
						property,
						claimed ? value : df[property],
					);
				continue;
			}
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
		frm.set_df_property("insights_chart", "description", "");
		if (!chart || !frappe.ui.mount_island) return;

		// a row of its own below the section's columns, as wide as the form
		const $el = $(`
			<div class="col-sm-12">
				<div class="insights-chart-preview">
					<div class="insights-chart-preview-header"></div>
					<div class="insights-chart-preview-body"></div>
				</div>
			</div>
		`).appendTo(frm.fields_dict.insights_chart.$wrapper.closest(".section-body"));
		$el.find(".insights-chart-preview").css({
			marginBottom: "var(--margin-lg)",
			padding: "var(--padding-md)",
			border: "1px solid var(--border-color)",
			borderRadius: "var(--border-radius-md)",
		});
		$el.find(".insights-chart-preview-body").css({ height: `${height}px` });
		const handle = frappe.ui.mount_island(
			"insights.chart",
			$el.find(".insights-chart-preview-body").get(0),
			{ chart, ...props },
		);
		frm.insights_preview = { chart, $el, handle };

		frappe
			.xcall("insights.desk.get_form_chart", { chart })
			.then((shown) => {
				if (!shown || frm.insights_preview?.chart !== chart) return;
				describe(frm, chart, shown);
			});
	}

	function describe(frm, chart, { title, workbook, can_share, label }) {
		// a new document is named as Show in Desk would name it, unless its
		// author typed a name of their own
		const typed =
			frm.doc[label_field] && frm.doc[label_field] !== frm.insights_label;
		if (frm.is_new() && label && !typed) {
			frm.insights_label = label;
			frm.set_value(label_field, label);
		}

		const url = `${frappe.boot.insights_path}/workbook/${encodeURIComponent(
			workbook,
		)}/chart/${encodeURIComponent(chart)}`;
		const link = (href, text) =>
			`<a href="${href}" target="_blank" rel="noopener">${text}</a>`;

		const sharing = __(
			"Users with an Insights role see it when the chart's sharing in Insights allows them.",
		);
		frm.set_df_property(
			"insights_chart",
			"description",
			can_share
				? `${sharing} ${link(`${url}?share=1`, __("Change sharing"))}`
				: sharing,
		);

		frm.insights_preview.$el
			.find(".insights-chart-preview-header")
			.css({
				display: "flex",
				alignItems: "center",
				justifyContent: "space-between",
				gap: "var(--margin-sm)",
				marginBottom: "var(--margin-md)",
			})
			.append(
				$(`<span class="text-base font-medium ellipsis"></span>`).text(
					title || chart,
				),
				$(link(url, __("Open in Insights"))).addClass(
					"text-muted small",
				),
			);
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
