app_name = "qsg_pmo"
app_title = "QSG PMO"
app_publisher = "QSG"
app_description = "PMO para coordinación de cuadrillas HFC/FTTH"
app_email = "ing.cpmo1@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "qsg_pmo",
# 		"logo": "/assets/qsg_pmo/logo.png",
# 		"title": "QSG PMO",
# 		"route": "/qsg_pmo",
# 		"has_permission": "qsg_pmo.api.permission.has_app_permission",
# 	}
# ]

# The dock, the rail down the left of the desk, is a document rather than a hook. Author it in
# Manage Dock on a developer-mode site and press Export to App, and it is written to
# `qsg_pmo/dock/qsg_pmo/qsg_pmo.json` for git to carry. An app that ships none has no
# rail: its sidebar gets a switcher in the header instead.
#
# A companion app, one that extends a host app rather than standing on its own, says so with
# `mount_on` on that same record, and its entries are appended to the host's rail. Mounting keeps
# the companion off the apps screen, so it takes precedence over any add_to_apps_screen above.

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/qsg_pmo/css/qsg_pmo.css"
# app_include_js = "/assets/qsg_pmo/js/qsg_pmo.js"

# include js, css files in header of web template
# web_include_css = "/assets/qsg_pmo/css/qsg_pmo.css"
# web_include_js = "/assets/qsg_pmo/js/qsg_pmo.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "qsg_pmo/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_kanban_js = {"doctype" : "public/js/doctype_kanban.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "qsg_pmo/public/icons.svg"

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

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "qsg_pmo.utils.jinja_methods",
# 	"filters": "qsg_pmo.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "qsg_pmo.install.before_install"
# after_install = "qsg_pmo.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "qsg_pmo.uninstall.before_uninstall"
# after_uninstall = "qsg_pmo.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "qsg_pmo.utils.before_app_install"
# after_app_install = "qsg_pmo.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "qsg_pmo.utils.before_app_uninstall"
# after_app_uninstall = "qsg_pmo.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "qsg_pmo.build.after_build"

# To hook into the build process of other apps
# The list of apps being built is passed as an argument

# after_app_build = "qsg_pmo.build.after_app_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "qsg_pmo.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["qsg_pmo.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
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

# scheduler_events = {
# 	"all": [
# 		"qsg_pmo.tasks.all"
# 	],
# 	"daily": [
# 		"qsg_pmo.tasks.daily"
# 	],
# 	"hourly": [
# 		"qsg_pmo.tasks.hourly"
# 	],
# 	"weekly": [
# 		"qsg_pmo.tasks.weekly"
# 	],
# 	"monthly": [
# 		"qsg_pmo.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "qsg_pmo.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "qsg_pmo.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "qsg_pmo.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "qsg_pmo.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["qsg_pmo.utils.before_request"]
# after_request = ["qsg_pmo.utils.after_request"]

# Job Events
# ----------
# before_job = ["qsg_pmo.utils.before_job"]
# after_job = ["qsg_pmo.utils.after_job"]

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
# 	"qsg_pmo.auth.validate"
# ]

# on_social_login = "qsg_pmo.auth.on_social_login"

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


# --- QSG PMO ---
required_apps = ["erpnext"]

before_install = "qsg_pmo.install.before_install"
after_install = "qsg_pmo.install.after_install"

scheduler_events = {
	"cron": {
		"*/15 * * * *": ["qsg_pmo.qsg_pmo.doctype.qsg_orden.qsg_orden.refresh_open_sla"],
	},
}

after_migrate = "qsg_pmo.install.after_migrate"

# --- Seguridad (qsg_pmo/seguridad) ---
# Permisos por fila: técnico → sus cuadrillas; supervisor → su contratista
permission_query_conditions = {
	"QSG Orden": "qsg_pmo.permissions.orden_query_conditions",
	"QSG Contratista": "qsg_pmo.permissions.contratista_query_conditions",
	"QSG Cuadrilla": "qsg_pmo.permissions.cuadrilla_query_conditions",
	"QSG Disponibilidad": "qsg_pmo.permissions.disponibilidad_query_conditions",
	"QSG Encuesta": "qsg_pmo.permissions.encuesta_query_conditions",
	"QSG Evaluacion Contratista": "qsg_pmo.permissions.evaluacion_query_conditions",
}
has_permission = {
	"QSG Orden": "qsg_pmo.permissions.orden_has_permission",
	"QSG Contratista": "qsg_pmo.permissions.contratista_has_permission",
	"QSG Cuadrilla": "qsg_pmo.permissions.cuadrilla_has_permission",
	"QSG Disponibilidad": "qsg_pmo.permissions.disponibilidad_has_permission",
	"QSG Encuesta": "qsg_pmo.permissions.encuesta_has_permission",
	"QSG Evaluacion Contratista": "qsg_pmo.permissions.evaluacion_has_permission",
}

# Solo imágenes reales y de tamaño acotado en los adjuntos de QSG
doc_events = {
	"File": {"before_insert": ["qsg_pmo.seguridad.archivos.on_file_insert"]},
}
# ... y se revisan antes de que Frappe toque el contenido
override_doctype_class = {"File": "qsg_pmo.seguridad.archivos.ArchivoQSG"}

# Cabeceras de seguridad y registro de eventos al final de cada petición
after_request = ["qsg_pmo.seguridad.cabeceras.after_request"]

# --- Inteligencia operativa (qsg_pmo/inteligencia) ---
# Bloque agregado: extiende lo anterior sin cambiarlo.
scheduler_events["cron"]["*/15 * * * *"].append("qsg_pmo.inteligencia.tareas.cada_15_minutos")
scheduler_events["cron"]["*/5 * * * *"] = ["qsg_pmo.inteligencia.tareas.cada_5_minutos"]
scheduler_events["hourly"] = ["qsg_pmo.inteligencia.tareas.cada_hora"]
scheduler_events["daily"] = ["qsg_pmo.inteligencia.tareas.diaria"]

# Municipios que faltaban, zona Islas, tipo HFC empresarial y valores de QSG Configuracion IA
after_migrate = [after_migrate, "qsg_pmo.inteligencia.semilla.completar"]

# Al aprobar un plan, ajusta las solicitudes de materiales al stock del camión (si se activa)
doc_events["QSG Plan de Despacho"] = {"on_update": ["qsg_pmo.inteligencia.servicio.al_actualizar_plan"]}

# Botones de inteligencia en formularios existentes, en archivos aparte
doctype_js = {
	"QSG Plan de Despacho": "public/js/plan_inteligente.js",
	"QSG Orden": "public/js/orden_inteligente.js",
}
