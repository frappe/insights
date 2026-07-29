declare global {
	interface Window {
		insights_path?: string
	}
}

// Sites can serve the app from a path other than /insights (site config
// `insights_path`); the server sends the effective one in boot data. Only the
// router base needs it — build links via router.resolve() so they pick this up.
export const APP_PATH = window.insights_path || '/insights'
