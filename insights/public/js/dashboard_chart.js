frappe.ui.form.on(
	"Dashboard Chart",
	insights.desk.chart_form({
		keep: [
			"chart_name",
			"insights_chart",
			"is_public",
			"roles",
			"is_standard",
			"module",
		],
		props: {},
		chart_types: ["!=", "Number"],
		height: 320,
	}),
);
