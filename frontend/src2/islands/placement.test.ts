import { describe, expect, it } from 'vitest'
import { placedDashboard } from './placement'

describe('the dashboard a placement asked for', () => {
	// @feature desk.dashboard-page
	it('reads the name off the page route', () => {
		expect(placedDashboard({ route: ['buying-dashboard'] })).toBe('buying-dashboard')
	})

	// @feature desk.dashboard-island
	it('keeps the name a claim passes outright', () => {
		expect(
			placedDashboard({ dashboard: 'selling-dashboard', route: ['buying-dashboard'] }),
		).toBe('selling-dashboard')
	})

	// @feature desk.dashboard-page
	it('names nothing when the placement named nothing', () => {
		expect(placedDashboard({ route: [] })).toBe('')
	})
})
