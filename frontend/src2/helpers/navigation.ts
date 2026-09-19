import type { RouteLocationRaw } from 'vue-router'

// The router is injected so the chart and dashboard graph never imports the SPA
// router: importing it drags every routed page into the bundle, and an island
// mounts without a router instance at all. The SPA registers its router in
// main.ts; a host that registers nothing resolves a string route as itself.

export type Router = {
	resolveHref: (to: RouteLocationRaw) => string
	navigate: (to: RouteLocationRaw) => void
}

let router: Router | null = null

export function setRouter(next: Router) {
	router = next
}

export function resolveHref(to: RouteLocationRaw): string {
	if (router) return router.resolveHref(to)
	return typeof to === 'string' ? to : ''
}

export function navigate(to: RouteLocationRaw) {
	if (router) return router.navigate(to)
	window.location.assign(resolveHref(to))
}
