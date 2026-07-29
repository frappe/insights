frappe.pages["insights"].on_page_load = function (wrapper) {
	// site config can move the app off /insights; boot carries the effective route
	const app = (frappe.boot.app_data || []).find(
		(a) => a.app_name === "insights",
	);
	window.location.href = app?.app_route || "/insights";
};
