frappe.ui.form.on(
	"Number Card",
	insights.desk.chart_form({
		keep: ["label", "insights_chart", "module"],
		props: { card: false },
		chart_types: "Number",
		height: 120,
	}),
);
