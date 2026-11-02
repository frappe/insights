import { describe, expect, it } from 'vitest'
import { rolesWithoutReadLines } from './roles_without_read'

describe('sharing a dashboard with roles', () => {
	// @feature permissions.roles-without-read
	it('names each chosen role that can’t read the dashboard’s charts and what it needs', () => {
		expect(
			rolesWithoutReadLines({
				'Sales User': ['Sales Invoice'],
				'Stock User': ['Item', 'Bin'],
			}),
		).toEqual(['Sales User can’t read Sales Invoice.', 'Stock User can’t read Item and Bin.'])
		expect(rolesWithoutReadLines({})).toEqual([])
	})
})
