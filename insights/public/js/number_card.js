frappe.ui.form.on(
	"Number Card",
	insights.desk.chart_form({
		keep: ["label", "insights_chart", "is_public", "is_standard", "module"],
		props: { card: false },
		chart_types: "Number",
		height: 120,
	}),
);
