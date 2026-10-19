import { beforeEach, describe, expect, it, vi } from 'vitest'

const session = vi.hoisted(() => {
	// the router patches `window.fetch` and reads the app path when it loads
	vi.stubGlobal('window', { fetch: () => {} })
	return { initialized: true, isLoggedIn: true, isAuthorized: false }
})

vi.mock('./session.ts', () => ({ default: session }))
vi.mock('vue-router', async (original) => {
	const router = await original<typeof import('vue-router')>()
	return { ...router, createWebHistory: router.createMemoryHistory }
})
vi.mock('./dashboard/DashboardList.vue', () => ({ default: {} }))
vi.mock('./dashboard/Dashboard.vue', () => ({ default: {} }))
vi.mock('./workbook/WorkbookList.vue', () => ({ default: {} }))

const { default: router } = await import('./router.ts')

async function open(path: string) {
	await router.push(path)
	return router.currentRoute.value.name
}

describe('a user without an Insights role', () => {
	beforeEach(async () => {
		session.isAuthorized = false
		await router.replace('/dashboards/start')
	})

	// @feature permissions.reader-app
	it('is sent to the dashboards list from a builder page', async () => {
		expect(await open('/workbook')).toBe('DashboardList')
		expect(await open('/data-source')).toBe('DashboardList')
	})

	// @feature permissions.reader-app
	it('opens a dashboard', async () => {
		expect(await open('/dashboards/selling')).toBe('Dashboard')
	})
})

describe('a user with an Insights role', () => {
	// @feature permissions.reader-app
	it('opens a builder page', async () => {
		session.isAuthorized = true
		expect(await open('/workbook')).toBe('WorkbookList')
	})
})
