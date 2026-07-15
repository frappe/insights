/**
 * Nudges ERPNext admins toward the prebuilt Insights dashboard for the module
 * workspace they're viewing (Selling, Buying, Stock, Financial Reports).
 *
 * Loaded on every desk page via `app_include_js` (hooks.py). Client Scripts are
 * DocType-scoped and never run on workspaces, so this app-level bundle is the
 * only place the banner can hook in. Kept tiny and gated early — it renders
 * nothing unless the route, role and dismissal checks all pass.
 */
(function () {
	if (window.__insights_nudge_loaded) return;
	window.__insights_nudge_loaded = true;

	const BASE = "/insights"; // v3 frontend base route
	const ALLOWED_ROLES = ["Insights Admin"];

	// Workspace -> shipped workbook template. `template` is the folder under
	// insights/workbook_templates/; the id is `insights/<template>`. The link opens
	// it via the SPA resolver, which lazily imports it (idempotent) on first open.
	const DASHBOARDS = {
		Selling: { title: "Sales Performance", template: "sales" },
		Buying: { title: "Purchasing Overview", template: "purchasing" },
		Stock: { title: "Stock & Inventory", template: "stock" },
		// "Accounts" module spans several workspaces — nudge from the reporting one.
		"Financial Reports": {
			title: "Receivables, Payables & Cash",
			template: "accounting",
		},
	};

	const templateId = (cfg) => `insights/${cfg.template}`;
	const openUrl = (cfg) => `${BASE}/template/${templateId(cfg)}`;

	const allowed = () =>
		ALLOWED_ROLES.some((r) => (frappe.user_roles || []).includes(r));
	// Site-wide opt-out for promotional banners — Frappe gates its own CRM/Helpdesk
	// workspace nudges (setup_promotional_banners) on the same System Settings flag.
	const suggestionsDisabled = () =>
		cint(frappe.sys_defaults?.disable_product_suggestion);
	const dismissKey = (ws) => `insights:nudge:${frappe.session.user}:${ws}`;
	const dismissed = (ws) => localStorage.getItem(dismissKey(ws)) === "1";
	const esc = (s) => frappe.utils.escape_html(s);

	// Self-guards on frappe.boot.enable_telemetry; no-ops when telemetry is off.
	const track = (event, ws, cfg) =>
		frappe.telemetry?.capture(event, "insights", {
			workspace: ws,
			template: templateId(cfg),
		});

	function currentWorkspace() {
		const route = frappe.get_route() || [];
		return route[0] === "Workspaces" ? route[1] : null;
	}

	function removeBanner() {
		document
			.querySelectorAll(".insights-nudge")
			.forEach((el) => el.remove());
	}

	// The visible workspace's main section. Workspaces share one reused body and
	// rebuild the editorjs content on each nav, so anchor against the stable direct
	// child `.editor-js-container` — a deep `.codex-editor` ref isn't a child of the
	// section and throws on client-side nav (only firstChild-fallback works on refresh).
	function findAnchor() {
		const sections = document.querySelectorAll(".layout-main-section");
		for (const s of sections) {
			if (s.offsetParent === null) continue; // not the active page
			return {
				container: s,
				before: s.querySelector(":scope > .editor-js-container"),
			};
		}
		return null;
	}

	function render(ws, cfg, anchor) {
		const el = document.createElement("div");
		el.className = "insights-nudge";
		el.setAttribute("role", "region");
		el.setAttribute("aria-label", "Insights dashboard suggestion");
		el.innerHTML = `
			<span class="insights-nudge__text">${__(
				"A prebuilt {0} dashboard is available in Insights",
				[`<b>${esc(cfg.title)}</b>`],
			)}</span>
			<span class="insights-nudge__actions">
				<a class="btn btn-default btn-sm insights-nudge__cta" href="${esc(
					openUrl(cfg),
				)}" target="_blank" rel="noopener">${frappe.utils.icon(
					"external-link",
					"sm",
				)}${__("Open")}</a>
				<button type="button" class="btn btn-default btn-sm icon-btn insights-nudge__x" aria-label="${__(
					"Dismiss",
				)}">${frappe.utils.icon("x", "sm")}</button>
			</span>`;
		el.querySelector(".insights-nudge__cta").addEventListener("click", () =>
			track("workspace_dashboard_nudge_clicked", ws, cfg),
		);
		el.querySelector(".insights-nudge__x").addEventListener("click", () => {
			localStorage.setItem(dismissKey(ws), "1");
			el.remove();
			track("workspace_dashboard_nudge_dismissed", ws, cfg);
		});
		anchor.container.insertBefore(
			el,
			anchor.before || anchor.container.firstChild,
		);
		track("workspace_dashboard_nudge_shown", ws, cfg);
	}

	function tryShow(attempt) {
		attempt = attempt || 0;
		const ws = currentWorkspace();
		const cfg = ws && DASHBOARDS[ws];
		if (!cfg || suggestionsDisabled() || !allowed() || dismissed(ws))
			return removeBanner();

		const anchor = findAnchor();
		if (!anchor) {
			if (attempt < 20) setTimeout(() => tryShow(attempt + 1), 100); // workspace renders async
			return;
		}
		removeBanner();
		render(ws, cfg, anchor);
	}

	function injectStyles() {
		if (document.getElementById("insights-nudge-styles")) return;
		const style = document.createElement("style");
		style.id = "insights-nudge-styles";
		style.textContent = `
			.insights-nudge {
				display: flex; align-items: center; gap: 16px;
				margin: 4px 0 -3px 0px; padding: 11px 14px;
				background: var(--surface-white);
				border: 1px solid var(--outline-gray-1);
				border-radius: var(--radius-lg, 10px);
			}
			.insights-nudge__text {
				flex: 1; min-width: 0;
				font-size: var(--text-base, 13px); line-height: 1.5;
				color: var(--ink-gray-6);
			}
			.insights-nudge__text b { font-weight: 600; color: var(--ink-gray-8); }
			.insights-nudge__actions { flex-shrink: 0; display: flex; align-items: center; gap: 6px; }
			.insights-nudge__cta { display: inline-flex; align-items: center; gap: 5px; white-space: nowrap; }
			.insights-nudge__cta svg { flex-shrink: 0; }
		`;
		document.head.appendChild(style);
	}

	function init() {
		if (!window.frappe || !frappe.router || !frappe.get_route) {
			return setTimeout(init, 300); // self-heal against load order
		}
		injectStyles();
		frappe.router.on("change", () => tryShow());
		tryShow();
	}

	init();
})();
