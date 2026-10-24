frappe.ui.form.on(
	"Dashboard Chart",
	insights.desk.chart_form({
		keep: ["chart_name", "insights_chart", "module"],
		label_field: "chart_name",
		props: {},
		chart_types: ["!=", "Number"],
		height: 360,
	}),
);
