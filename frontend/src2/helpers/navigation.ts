import type { RouteLocationRaw } from 'vue-router'

// Navigation is injected so the chart and dashboard graph never imports the SPA
// router: importing it drags every routed page into the bundle, and an island
// mounts without a router instance at all. The SPA registers its router in
// main.ts; a host that registers nothing falls back to a full page load.

export type NavigationProvider = {
	resolveHref: (to: RouteLocationRaw) => string
	navigate: (to: RouteLocationRaw) => void
}

let provider: NavigationProvider | null = null

export function setNavigationProvider(navigationProvider: NavigationProvider) {
	provider = navigationProvider
}

export function resolveHref(to: RouteLocationRaw): string {
	if (provider) return provider.resolveHref(to)
	return typeof to === 'string' ? to : ''
}

export function navigate(to: RouteLocationRaw) {
	if (provider) return provider.navigate(to)
	const href = resolveHref(to)
	if (href) window.location.assign(href)
}
