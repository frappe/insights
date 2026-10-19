import { Building2, Lock, ShieldCheck, Users } from 'lucide-vue-next'
import { describe, expect, it, vi } from 'vitest'
import { access } from './access'

vi.mock('../session', () => ({ default: { user: {} } }))

const name = (email: string) => email.split('@')[0]

describe('who a workbook is shared with', () => {
	// @feature workbook.list
	it('names roles and people in one label, under the roles icon', () => {
		expect(
			access({ visible_to_roles: ['Sales User'], shared_with: ['ann@x.com'] }, name),
		).toEqual({
			icon: ShieldCheck,
			label: 'Sales User, ann',
		})
		expect(
			access({ visible_to_roles: ['A', 'B'], shared_with: ['ann@x.com', 'bob@x.com'] }, name),
		).toEqual({ icon: ShieldCheck, label: '2 roles, 2 people' })
	})

	// @feature workbook.list
	it('names roles, people, everyone or no one alone', () => {
		expect(access({ visible_to_roles: ['Sales User'] }, name)).toEqual({
			icon: ShieldCheck,
			label: 'Sales User',
		})
		expect(access({ shared_with: ['ann@x.com'] }, name)).toEqual({ icon: Users, label: 'ann' })
		expect(access({ shared_with_organization: true }, name)).toEqual({
			icon: Building2,
			label: 'Everyone',
		})
		expect(access({}, name)).toEqual({ icon: Lock, label: 'Private' })
	})
})
