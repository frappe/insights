frappe.provide("frappe.ui.form");

frappe.ui.form.QueryFieldQuickEntryForm = class QueryFieldQuickEntryForm extends (
	frappe.ui.form.QuickEntryForm
) {
	render_dialog() {
		super.render_dialog();
		if (this.dialog.fields_dict["field"]) {
			this.dialog.fields_dict["field"].get_query = () => {
				return {
					query: "frappe_analytics.api.queries.get_doctype_and_field_options",
				};
			};
		}
	}
};
