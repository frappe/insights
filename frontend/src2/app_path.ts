declare global {
	interface Window {
		insights_path?: string
	}
}

/**
 * Where this site serves the Insights app from (site config `insights_path`).
 *
 * The server decides it and publishes it on every page that can host Insights:
 * the app's own www page puts it in the page boot, and `insights.desk`'s
 * `extend_bootinfo` puts it in desk's. A desk island reads the second one — it
 * builds every link it offers out of this, and without it a site that mounted
 * the app elsewhere sends every reader of an island to a 404.
 *
 * Inside the SPA only the router base needs it: build links via
 * router.resolve() so they pick this up.
 */
export const APP_PATH =
	window.insights_path || (window as any).frappe?.boot?.insights_path || '/insights'
