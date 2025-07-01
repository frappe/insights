// redirect to desk page 'insights' after setup wizard is complete
// 'insights' desk page redirects to '/insights'

frappe.setup.welcome_page = "/app/insights";


frappe.setup.on("before_load", function () {
	// if setup wizard is already completed for ERPNext, skip the setup wizard
    if (
        frappe.boot.setup_wizard_completed_apps?.length &&
        frappe.boot.setup_wizard_completed_apps.includes("frappe")
    ) {
        complete_setup_wizard();
        return;
    }
});

function complete_setup_wizard() {
    frappe.call({
        method: "insights.setup.setup_wizard.enable_setup_wizard_complete",
        callback: function (r) {
            frappe.ui.toolbar.clear_cache();
        }
    })
}