declare global {
	interface Window {
		insights_path?: string
	}
}

/**
 * The path this site serves the Insights app from (site config `insights_path`).
 *
 * The server sends it in two places. The app's www page puts it in the page
 * boot. `extend_bootinfo` in `insights.desk` puts it in desk's boot, and a desk
 * island reads it from there. The island builds its links from this path.
 * Without it, a site that serves the app elsewhere gives the island's links a
 * 404.
 *
 * Inside the SPA only the router base needs it. Build links with
 * router.resolve() so they use it.
 */
export const APP_PATH =
	window.insights_path || (window as any).frappe?.boot?.insights_path || '/insights'
