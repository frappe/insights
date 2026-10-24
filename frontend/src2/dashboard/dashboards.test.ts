import { describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

// the page keeps the view in the browser's storage, which Node lacks
vi.hoisted(() => {
	const stored = new Map<string, string>()
	const storage = {
		getItem: (key: string) => stored.get(key) ?? null,
		setItem: (key: string, value: string) => stored.set(key, String(value)),
		removeItem: (key: string) => stored.delete(key),
	}
	Object.defineProperty(globalThis, 'localStorage', { value: storage, configurable: true })
})

const session = vi.hoisted(() => ({ user: { email: 'ann@x.com' }, isAuthorized: true }))
vi.mock('../session', () => ({ default: session }))

import { useDashboardView } from './dashboards'

describe('the Dashboards view', () => {
	// @feature dashboard.list-view
	it('opens as a list, and each user keeps their own pick', async () => {
		expect(useDashboardView().value).toBe('list')
		useDashboardView().value = 'grid'
		await nextTick()
		expect(useDashboardView().value).toBe('grid')

		session.user.email = 'bob@x.com'
		expect(useDashboardView().value).toBe('list')
	})
})
