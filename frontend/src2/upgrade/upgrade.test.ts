import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, reactive } from 'vue'
import type { UpgradeItem } from './upgrade'

const call = vi.hoisted(() => vi.fn())
vi.mock('frappe-ui', () => ({ call }))
vi.mock('../helpers', () => ({ showErrorToast: vi.fn() }))

const session = vi.hoisted(() => ({
	user: {} as Record<string, any>,
}))
vi.mock('../session', () => ({ default: session }))

const stored = vi.hoisted(() => {
	const values = new Map<string, string>()
	const storage = {
		getItem: (key: string) => values.get(key) ?? null,
		setItem: (key: string, value: string) => values.set(key, value),
		removeItem: (key: string) => values.delete(key),
	}
	vi.stubGlobal('localStorage', storage)
	return values
})

const DAVE = 'dave@fixture.test'
const BOB = 'bob@fixture.test'

function item(name: string, code: string, data: Record<string, any>): UpgradeItem {
	return {
		name,
		code,
		status: 'Open',
		message: '',
		reference_doctype: null,
		reference_name: null,
		user: null,
		action: null,
		data,
		people: {},
		workbook: null,
		form_url: null,
		can_fix: false,
	}
}

const ITEMS = [
	item('access', 'P17', { user: BOB, doctypes: ['Customer'] }),
	item('range', 'K1', { dashboard: 'Sales', start: '2024-01-01', end: '2024-03-31' }),
]

async function wizard(items: UpgradeItem[] = ITEMS) {
	vi.resetModules()
	session.user = reactive({ email: DAVE, is_upgrade_admin: true, upgrade_unseen: false })
	call.mockReset()
	call.mockImplementation(async (method: string, args?: { names: string[] }) => {
		if (method === 'insights.api.upgrade.get_upgrade_items') return items
		if (method === 'insights.api.upgrade.dismiss_upgrade_items') return args!.names
		if (method === 'insights.api.upgrade.reopen_upgrade_items') return args!.names
		if (method === 'insights.api.upgrade.fix_upgrade_item') return null
	})
	const { default: upgrade } = await import('./upgrade')
	await upgrade.load()
	return upgrade
}

beforeEach(() => stored.clear())

describe('the upgrade wizard', () => {
	// @feature upgrade.wizard
	it('keeps where the reader left it per user', async () => {
		const upgrade = await wizard()
		await upgrade.open()
		upgrade.goTo('numbers')
		await nextTick()

		expect(JSON.parse(stored.get(`insights:upgrade-wizard:${DAVE}`)!).step).toBe('numbers')
		expect(upgrade.steps[upgrade.stepIndex].id).toBe('numbers')
	})

	// @feature upgrade.wizard
	it('resumes after finishing at the first step with an open item', async () => {
		const upgrade = await wizard()
		await upgrade.open()
		await upgrade.finish()
		expect(upgrade.progress.finished).toBe(true)

		await upgrade.resume()
		expect(upgrade.progress.finished).toBe(false)
		expect(upgrade.steps[upgrade.stepIndex].id).toBe('access')
	})

	// @feature upgrade.wizard
	it('resumes at the next step once the stored one has no items left', async () => {
		const upgrade = await wizard([ITEMS[1]])
		await upgrade.open()
		upgrade.progress.step = 'access'
		expect(upgrade.steps[upgrade.stepIndex].id).toBe('numbers')
	})

	// @feature upgrade.wizard
	it('closes every item of a row in one call', async () => {
		const upgrade = await wizard()
		await upgrade.markDone(['access'])

		expect(call).toHaveBeenCalledWith('insights.api.upgrade.dismiss_upgrade_items', {
			names: ['access'],
		})
		expect(upgrade.isDone('access')).toBe(true)
		expect(upgrade.openWizardItems.map((row) => row.item.name)).toEqual(['range'])
		expect(upgrade.steps.map((step) => step.id)).toContain('access')
	})

	// @feature upgrade.attention-fix
	it('deletes an unchanged template copy through its fix, and counts it done', async () => {
		const copy = {
			...item('copy', 'W2', { workbook: 'Sales Performance', standard: 'Selling' }),
			action: 'delete_workbook' as const,
			can_fix: true,
		}
		const upgrade = await wizard([
			...ITEMS.map((i) => ({ ...i, status: 'Open' as const })),
			copy,
		])
		await upgrade.fix(copy)

		expect(call).toHaveBeenCalledWith('insights.api.upgrade.fix_upgrade_item', { name: 'copy' })
		expect(upgrade.items.find((i) => i.name === 'copy')!.status).toBe('Done')
		expect(upgrade.openWizardItems.map((row) => row.item.name)).toEqual(['access', 'range'])
	})

	// @feature upgrade.wizard
	it('keeps an item closed before in its step, counted as done, and puts it back on Undo', async () => {
		const upgrade = await wizard([{ ...ITEMS[0], status: 'Dismissed' }, ITEMS[1]])
		session.user.upgrade_item_count = 1

		expect(upgrade.steps.map((step) => step.id)).toContain('access')
		expect(upgrade.isDone('access')).toBe(true)
		expect(upgrade.openWizardItems.map((row) => row.item.name)).toEqual(['range'])

		await upgrade.reopen(['access'])

		expect(call).toHaveBeenCalledWith('insights.api.upgrade.reopen_upgrade_items', {
			names: ['access'],
		})
		expect(upgrade.isDone('access')).toBe(false)
		expect(upgrade.openWizardItems.map((row) => row.item.name)).toEqual(['access', 'range'])
		expect(session.user.upgrade_item_count).toBe(2)
	})

	// @feature upgrade.users-welcomed
	it('opens by itself until the reader finishes or skips it, and a close puts it away for the visit', async () => {
		const upgrade = await wizard([])
		session.user.upgrade_unseen = true
		await upgrade.open()

		await upgrade.close()
		expect(upgrade.showWizard).toBe(false)
		expect(upgrade.progress.finished).toBe(false)
		expect(session.user.upgrade_unseen).toBe(true)
		expect(call).not.toHaveBeenCalledWith('insights.api.upgrade.mark_upgrade_seen')

		await upgrade.open()
		await upgrade.finish()
		expect(upgrade.progress.finished).toBe(true)
		expect(session.user.upgrade_unseen).toBe(false)
		expect(call).toHaveBeenCalledWith('insights.api.upgrade.mark_upgrade_seen')
	})

	// @feature upgrade.users-welcomed
	it('does not open by itself over a page it opened in a new tab', async () => {
		const upgrade = await wizard([])
		session.user.upgrade_unseen = true
		const { linkFromWizard } = await import('./upgrade')

		const route = linkFromWizard({ name: 'Workbook', query: { share: '1' } })
		expect(route.query).toEqual({ share: '1', from_upgrade: '1' })

		const at = (search: string) => {
			vi.stubGlobal('window', { location: { search } })
			return upgrade.opensByItself()
		}
		expect(at('?share=1&from_upgrade=1')).toBe(false)
		expect(at('?share=1')).toBe(true)
		session.user.upgrade_unseen = false
		expect(at('')).toBe(false)
		// unstubbing every global would take the hoisted localStorage too
		vi.stubGlobal('window', undefined)
	})
})
