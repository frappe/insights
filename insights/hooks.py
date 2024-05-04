from . import __version__ as app_version

app_name = "insights"
app_title = "Frappe Insights"
app_publisher = "Frappe Technologies Pvt. Ltd."
app_description = "Powerful Reporting Tool for Frappe Apps"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "hello@frappe.io"
app_license = "GNU GPLv3"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/insights/css/insights.css"
# app_include_js = "insights.bundle.js"

# include js, css files in header of web template
# web_include_css = "/assets/insights/css/insights.css"
# web_include_js = "/assets/insights/js/insights.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "insights/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "insights.utils.jinja_methods",
# 	"filters": "insights.utils.jinja_filters"
# }

# Setup
# ------------
setup_wizard_requires = "assets/insights/js/setup_wizard.js"
setup_wizard_stages = "insights.setup.setup_wizard.get_setup_stages"

# Installation
# ------------

# before_install = "insights.install.before_install"
# after_install = "insights.setup.after_install"
# after_migrate = ["insights.migrate.after_migrate"]

fixtures = [
    {
        "dt": "Insights Data Source",
        "filters": {"name": ("in", ["Site DB", "Query Store"])},
    }
]

# Uninstallation
# ------------

# before_uninstall = "insights.uninstall.before_uninstall"
# after_uninstall = "insights.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "insights.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
has_permission = {
    "Insights Data Source": "insights.overrides.has_permission",
    "Insights Table": "insights.overrides.has_permission",
    "Insights Query": "insights.overrides.has_permission",
    "Insights Dashboard": "insights.overrides.has_permission",
}

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {"all": ["insights.insights.doctype.insights_alert.insights_alert.send_alerts"]}

# Testing
# -------

before_tests = "insights.tests.utils.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "insights.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "insights.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"insights.auth.validate"
# ]

website_route_rules = [
    {"from_route": "/insights/<path:app_path>", "to_route": "insights"},
]
