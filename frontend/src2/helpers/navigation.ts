import type { RouteLocationRaw } from 'vue-router'

// The router is injected so chart and dashboard modules never import the SPA
// router. Importing it pulls every routed page into the bundle, and an island
// has no router instance. The SPA registers its router in main.ts. With no
// router registered, a string route is used as the href unchanged.

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
