frappe.ui.form.on(
	"Dashboard Chart",
	insights.desk.chart_form({
		keep: ["chart_name", "insights_chart", "module"],
		props: {},
		chart_types: ["!=", "Number"],
		height: 360,
	}),
);
