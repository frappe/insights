/**
 * Nudges ERPNext admins toward the prebuilt Insights dashboard for the module
 * workspace they're viewing.
 *
 * Loaded on every desk page via `app_include_js` (hooks.py): Client Scripts are
 * DocType-scoped and never run on workspaces, so this is the only place the
 * banner can hook in.
 */
(function () {
	if (window.__insights_nudge_loaded) return;
	window.__insights_nudge_loaded = true;

	// site config can move the app off /insights
	const BASE =
		(frappe.boot.app_data || []).find((a) => a.app_name === "insights")
			?.app_route || "/insights";
	const ALLOWED_ROLES = ["Insights Admin"];

	// A workspace only reaches its own page (and this banner) when its sidebar
	// starts with a "Home" item linking back to itself — otherwise the desk lands
	// on the first report instead. "Financial Reports" has no such item, so the
	// accounting nudge hangs off "Accounting" too.
	// Each dashboard ships in a bundle and exists on every site after migrate,
	// so the link is just its slug — no import to trigger, nothing to prepare.
	const ACCOUNTING = {
		title: "Receivables, Payables & Cash",
		slug: "receivables-payables-cash",
	};
	const DASHBOARDS = {
		Selling: { title: "Sales Performance", slug: "sales-performance" },
		Buying: { title: "Purchasing Overview", slug: "purchasing-overview" },
		Stock: { title: "Inventory Health", slug: "inventory-health" },
		Accounting: ACCOUNTING,
		"Financial Reports": ACCOUNTING,
	};

	const openUrl = (cfg) => `${BASE}/dashboards/${cfg.slug}`;

	const allowed = () =>
		ALLOWED_ROLES.some((r) => (frappe.user_roles || []).includes(r));
	// Frappe gates its own CRM/Helpdesk workspace nudges on the same flag.
	const suggestionsDisabled = () =>
		cint(frappe.sys_defaults?.disable_product_suggestion);
	// Keyed on the dashboard, not the workspace, so dismissing the suggestion once
	// covers every workspace that offers it.
	const dismissKey = (cfg) =>
		`insights:nudge:${frappe.session.user}:${cfg.slug}`;
	const dismissed = (cfg) => localStorage.getItem(dismissKey(cfg)) === "1";
	const esc = (s) => frappe.utils.escape_html(s);

	// no-ops when telemetry is off
	const track = (event, ws, cfg) =>
		frappe.telemetry?.capture(event, "insights", {
			workspace: ws,
			dashboard: cfg.slug,
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

	// Workspaces share one reused body and rebuild the editorjs content on each
	// nav, so anchor against the stable direct child `.editor-js-container` — a
	// deep `.codex-editor` ref isn't a child of the section and throws on
	// client-side nav (only firstChild-fallback works on refresh).
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
			localStorage.setItem(dismissKey(cfg), "1");
			el.remove();
			track("workspace_dashboard_nudge_dismissed", ws, cfg);
		});
		anchor.container.insertBefore(
			el,
			anchor.before || anchor.container.firstChild,
		);
		track("workspace_dashboard_nudge_shown", ws, cfg);
	}

	let retryTimer = null;
	function tryShow(attempt) {
		attempt = attempt || 0;
		// Supersede any pending retry: a fresh call (e.g. a fast navigation) owns
		// the banner now, so stale chains can't double-render it or re-fire "shown".
		clearTimeout(retryTimer);
		const ws = currentWorkspace();
		const cfg = ws && DASHBOARDS[ws];
		if (!cfg || suggestionsDisabled() || !allowed() || dismissed(cfg))
			return removeBanner();

		const anchor = findAnchor();
		if (!anchor) {
			if (attempt < 20)
				retryTimer = setTimeout(() => tryShow(attempt + 1), 100); // workspace renders async
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
