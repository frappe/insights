import { describe, expect, it, vi } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import type { UpgradeItem } from './upgrade'
import {
	cardDescription,
	stepBadge,
	keyAction,
	nextOpenIndex,
	pictureOf,
	sentenceOf,
	featuresFor,
	groups,
	PICTURES,
	type PictureName,
	startIndex,
	stepIndexOf,
	wizardSteps,
	type Part,
} from './upgrade_steps'
import UpgradePicture from './pictures/UpgradePicture.vue'

// a picture's sample rows name the apps that ship dashboards, which only a site knows
vi.mock('frappe-ui', async (importOriginal) => ({
	...(await importOriginal<object>()),
	call: () => Promise.resolve([]),
}))

const BOB = 'bob@fixture.test'
const ALICE = 'alice@fixture.test'
const DAVE = 'dave@fixture.test'

const can = (share: boolean) => ({ readStandardDashboards: false, showInDesk: false, share })

const people = {
	[BOB]: { full_name: 'Bob Fixture', first_name: 'Bob' },
	[ALICE]: { full_name: 'Alice Fixture', first_name: 'Alice' },
	[DAVE]: { full_name: 'Dave Fixture', first_name: 'Dave' },
}

function item(name: string, code: string, data: Record<string, any> = {}, extra = {}): UpgradeItem {
	return {
		name,
		code,
		status: 'Open',
		message: `${code} message`,
		reference_doctype: null,
		reference_name: null,
		user: null,
		action: null,
		data,
		people,
		workbook: null,
		form_url: null,
		can_fix: false,
		...extra,
	}
}

const text = (parts: Part[] | undefined) => (parts ?? []).map((part) => part.text).join('')
const names = (parts: Part[] | undefined) =>
	(parts ?? []).filter((part) => part.em).map((part) => part.text)

describe('the wizard steps', () => {
	// @feature upgrade.wizard
	it('leave out a step with nothing in it, and put each group of items in one step', () => {
		const items = [
			item('a', 'P17', { user: BOB, doctypes: ['Sales Invoice'] }),
			item('b', 'P3', { workbook: 'Sales', users: [BOB] }),
			item('c', 'P7', { workbook: 'Sales', users: [], shared: [], removed: [] }),
			item('d', 'W2', { workbook: 'Sales Performance', standard: 'Selling', app: 'ERPNext' }),
		]
		expect(
			wizardSteps(items, { can: can(true), admin: true, me: DAVE }).map((step) => step.id),
		).toEqual([
			'welcome',
			'charts',
			'drill',
			'sharing',
			'roles',
			'access',
			'workbooks',
			'copies',
		])
		expect(
			wizardSteps([], { can: can(false), admin: true, me: DAVE }).map((step) => step.id),
		).toEqual(['welcome', 'charts', 'drill'])
	})

	// @feature upgrade.wizard
	it('show one row for the two items that tell both people of one change', () => {
		const data = { chart: 'Bob published, script rows', publisher: BOB, owner: ALICE }
		const reference = { reference_doctype: 'Insights Chart v3', reference_name: 'kvubr6gkub' }
		const steps = wizardSteps(
			[
				item('to-alice', 'P10', data, { ...reference, user: ALICE }),
				item('to-bob', 'P10', data, { ...reference, user: BOB }),
			],
			{ can: can(true), admin: true, me: DAVE },
		)
		const publicCharts = steps.find((step) => step.id === 'public')!
		expect('rows' in publicCharts && publicCharts.rows.map((row) => row.names)).toEqual([
			['to-alice', 'to-bob'],
		])
	})

	// @feature upgrade.wizard
	it('put every item the reader works through in one row, so the card counts what the server does', () => {
		const items = [
			item('a', 'P17', { user: BOB, doctypes: ['Sales Invoice'] }),
			item('b', 'P10', { chart: 'Trend', owner: ALICE, reason: 'script' }, { user: ALICE }),
			item('c', 'P21', { query: 'Origin', workbook: 'Sales', variables: ['api_token'] }),
			item('d', 'P11', { chart: 'KPIs', publisher: DAVE, owner: ALICE }, { user: DAVE }),
		]
		const steps = wizardSteps(items, { can: can(true), admin: true, me: DAVE })
		const names = steps.flatMap((step) =>
			'rows' in step ? step.rows.flatMap((row) => row.names) : [],
		)
		expect(names.sort()).toEqual(['a', 'b', 'c', 'd'])
	})
})

describe('the wizard steps of an admin', () => {
	// @feature upgrade.wizard
	it('hold the items outside the groups that are addressed to no one, as Administrator’s work is', () => {
		const items = [
			item('secret', 'P21', { query: 'Origin', workbook: 'Sales', variables: ['api_token'] }),
			item('cache', 'J1', { alert: 'Watch a cache', chart: 'Trend' }),
		]
		const steps = wizardSteps(items, { can: can(true), admin: true, me: DAVE })
		const notes = steps.find((step) => step.id === 'notes')!
		expect('rows' in notes && notes.rows.map((row) => row.item.code)).toEqual(['P21', 'J1'])
		expect('group' in notes && notes.group.kind).toBe('now')
		expect('group' in notes && notes.group.title).toBe('A few more changes')
	})
})

describe('what is new', () => {
	// @feature upgrade.wizard
	it('shows a feature only to someone who can do what it shows', () => {
		const ids = (has: Partial<Parameters<typeof featuresFor>[0]>) =>
			featuresFor({ ...can(false), ...has }).map((feature) => feature.id)
		expect(ids({})).toEqual(['charts', 'drill'])
		expect(ids({ share: true })).toEqual(['charts', 'drill', 'sharing', 'roles'])
		expect(ids({ readStandardDashboards: true, showInDesk: true, share: true })).toEqual([
			'charts',
			'drill',
			'standard',
			'desk',
			'sharing',
			'roles',
		])
	})
})

describe('resuming the wizard', () => {
	const steps = wizardSteps(
		[
			item('a', 'P17', { user: BOB, doctypes: ['Customer'] }),
			item('b', 'K1', { dashboard: 'Sales', start: '2024-01-01', end: '2024-03-31' }),
		],
		{ can: can(true), admin: true, me: DAVE },
	)

	// @feature upgrade.wizard
	it('opens at the stored step', () => {
		expect(steps[stepIndexOf(steps, 'access')].id).toBe('access')
	})

	// @feature upgrade.wizard
	it('goes on to the next step when the stored one has no items left', () => {
		expect(steps[stepIndexOf(steps, 'workbooks')].id).toBe('numbers')
		expect(steps[stepIndexOf(steps, 'notes')].id).toBe('numbers')
		expect(steps[stepIndexOf(steps, 'no-such-step')].id).toBe('welcome')
	})
})

describe('the wizard steps of someone who is not an admin', () => {
	// @feature upgrade.wizard
	it('hold their own items outside the groups in Good to know', () => {
		const items = [
			item('moved', 'P11', { chart: 'KPIs', publisher: BOB, owner: ALICE }, { user: ALICE }),
			item('script', 'P20', { title: 'Script rows', author: ALICE }, { user: ALICE }),
		]
		const steps = wizardSteps(items, { can: can(true), admin: false, me: ALICE })
		const notes = steps.find((step) => step.id === 'notes')!
		expect('rows' in notes && notes.rows.map((row) => row.item.code)).toEqual(['P11', 'P20'])
		expect('group' in notes && notes.group.title).toBe('A few changes to what you made')
		expect('group' in notes && notes.group.picture).toBeUndefined()
		expect(items.map(pictureOf)).toEqual(['chartOwner', undefined])
	})

	// @feature upgrade.wizard
	it('ask for them in Good to know when an item there tells of a failure', () => {
		const kind = (items: UpgradeItem[]) => {
			const steps = wizardSteps(items, { can: can(true), admin: false, me: ALICE })
			const notes = steps.find((step) => step.id === 'notes')!
			return 'group' in notes && notes.group.kind
		}
		const moved = item('moved', 'P11', { chart: 'KPIs', publisher: BOB, owner: ALICE })
		const script = item('script', 'P20', { title: 'Script rows', author: ALICE })
		expect(kind([moved, script])).toBe('note')
		expect(kind([moved, item('fails', 'Q1', { title: 'Raw rows', names: ['sleep'] })])).toBe(
			'now',
		)
		expect(kind([item('import', 'J4', { title: 'Nightly', names: ['sleep'] })])).toBe('now')
		const unpublished = item('gone', 'P11', { ...moved.data, publisher_disabled: true })
		expect(kind([unpublished])).toBe('now')
	})
})

describe('an item sentence', () => {
	// @feature upgrade.item-sentences
	it('names the people it is about, and says "you" only to that person', () => {
		const access = item('a', 'P17', { user: BOB, doctypes: ['Sales Invoice'] })
		const toDave = sentenceOf(access, DAVE)
		expect(text(toDave.text)).toBe('Bob can’t see charts on Sales Invoices any more.')
		expect(names(toDave.text)).toEqual(['Bob', 'Sales Invoices'])
		expect(text(toDave.todo)).toBe('Give Bob a desk role that can read them.')

		const toBob = sentenceOf(access, BOB)
		expect(text(toBob.text)).toBe('You can’t see charts on Sales Invoices any more.')
		expect(text(toBob.todo)).toBe('Give yourself a desk role that can read them.')
	})

	// @feature upgrade.item-sentences
	it('names both sides of a moved chart', () => {
		const moved = item('a', 'P11', { chart: 'Script rows', publisher: BOB, owner: ALICE })
		expect(text(sentenceOf(moved, DAVE).text)).toBe(
			'The Script rows chart now belongs to Bob, who published it, instead of Alice. Its readers see the same rows as before.',
		)
		expect(names(sentenceOf(moved, ALICE).text)).toEqual(['Script rows', 'Bob', 'you'])
	})

	// @feature upgrade.item-sentences
	it('says readers of a public chart see Not Permitted when it runs as someone who can’t read it', () => {
		const form = { form_url: '/desk/user/alice' }
		const owner = sentenceOf(
			item(
				'a',
				'P10',
				{ chart: 'Trend', owner: ALICE, reason: 'unreadable', doctypes: ['Sales Invoice'] },
				form,
			),
			DAVE,
		)
		expect(text(owner.text)).toBe(
			'The Trend chart runs as Alice, who can’t read Sales Invoices, so everyone who opens it sees Not Permitted.',
		)
		expect(text(owner.todo)).toBe('Give Alice a desk role that can read them.')
		expect(owner.action).toEqual({
			kind: 'form',
			label: 'Open Alice’s roles',
			url: '/desk/user/alice',
		})

		const moved = sentenceOf(
			item('b', 'P11', {
				chart: 'Site rows',
				publisher: BOB,
				owner: ALICE,
				doctypes: ['Sales Invoice'],
			}),
			ALICE,
		)
		expect(text(moved.text)).toBe(
			'The Site rows chart now belongs to Bob, who published it, instead of you. Bob can’t read Sales Invoices, so its readers see Not Permitted.',
		)
		// a table off the site database needs a team grant, not a role
		const team = sentenceOf(
			item(
				'c',
				'P10',
				{ chart: 'Trend', owner: ALICE, reason: 'unreadable', doctypes: [] },
				{
					...form,
					workbook: '9',
					reference_doctype: 'Insights Chart v3',
					reference_name: 'c1',
				},
			),
			DAVE,
		)
		expect(text(team.text)).toContain('who can’t read its tables')
		expect(team.todo).toBeUndefined()
		expect(team.action).toMatchObject({ kind: 'route', label: 'Open chart' })
	})

	// @feature upgrade.item-sentences
	it('titles the Public charts step by what holds for each of its items', () => {
		const step = groups().find((group) => group.id === 'public')!
		expect(step.title).toBe('Public charts run as their owner')
		expect(step.lead.join(' ')).not.toContain('owner’s rows')
	})

	// @feature upgrade.item-sentences
	it('lists three doctypes and counts the rest', () => {
		const many = item('a', 'P17', {
			user: DAVE,
			doctypes: ['Company', 'Customer', 'Item', 'Purchase Invoice', 'Quotation'],
		})
		expect(text(sentenceOf(many, DAVE).text)).toBe(
			'You can’t see charts on Companies, Customers, Items and 2 more any more.',
		)
	})

	// @feature upgrade.item-sentences
	it('tells a doctype someone can no longer read from one desk now narrows', () => {
		const both = item('a', 'P17', {
			user: BOB,
			doctypes: ['Customer'],
			narrowed: ['Sales Invoice'],
		})
		expect(text(sentenceOf(both, DAVE).text)).toBe(
			'Bob can’t see charts on Customers any more, and sees only the rows desk gives them of Sales Invoices.',
		)
		expect(text(sentenceOf(both, BOB).text)).toBe(
			'You can’t see charts on Customers any more, and see only the rows desk gives you of Sales Invoices.',
		)

		const narrowed = item('b', 'P17', { user: BOB, doctypes: [], narrowed: ['Sales Invoice'] })
		expect(text(sentenceOf(narrowed, DAVE).text)).toBe(
			'Bob now sees only the rows desk gives them of Sales Invoices.',
		)
		expect(text(sentenceOf(narrowed, BOB).text)).toBe(
			'You now see only the rows desk gives you of Sales Invoices.',
		)
		expect(sentenceOf(narrowed, DAVE).todo).toBeUndefined()
	})

	// @feature upgrade.item-sentences
	it('joins the titles of the documents a team let someone edit', () => {
		const edited = item('a', 'P4', {
			workbook: 'Sales',
			users: [BOB],
			teams: ['Sales team'],
			items: ['Revenue', 'Margin', 'Orders'],
		})
		expect(names(sentenceOf(edited, DAVE).text)).toEqual(
			expect.arrayContaining(['Revenue', 'Margin', 'Orders']),
		)
		expect(text(sentenceOf(edited, DAVE).text)).toContain('Revenue, Margin and Orders')
	})

	// @feature upgrade.item-sentences
	it('reads a team rule as words when it is a plain comparison', () => {
		const team = item('a', 'P17', {
			team: 'Sales team',
			members: [ALICE, BOB],
			restrictions: [
				{
					doctype: 'Sales Invoice',
					condition: "company == 'Kaveri Traders'",
					field: 'company',
					value: 'Kaveri Traders',
				},
			],
		})
		expect(text(sentenceOf(team, DAVE).text)).toBe(
			'The Sales team limited Alice and Bob to Sales Invoices where company is Kaveri Traders. That rule no longer applies.',
		)
	})

	// @feature upgrade.item-sentences
	it('lists every rule a team had', () => {
		const team = item('a', 'P17', {
			team: 'Sales team',
			members: [ALICE],
			restrictions: [
				{ doctype: 'Sales Invoice', field: 'company', value: 'Kaveri Traders' },
				{ doctype: 'Customer', field: 'customer_group', value: 'Commercial' },
				{ doctype: 'Item', condition: "item_group like 'Raw%'" },
			],
		})
		expect(text(sentenceOf(team, DAVE).text)).toBe(
			"The Sales team limited Alice to Sales Invoices where company is Kaveri Traders, Customers where customer group is Commercial and Items where item_group like 'Raw%'. Those rules no longer apply.",
		)
	})

	// @feature upgrade.item-sentences
	it('says every change to a workbook’s access: who gained it and each share removed', () => {
		const one = item('a', 'P7', {
			workbook: 'Sales',
			users: [],
			shared: [],
			removed: [{ kind: 'chart', title: 'Revenue', write: true }],
		})
		expect(text(sentenceOf(one, DAVE).text)).toBe(
			'Everyone could edit the Revenue chart. That share is gone, so only people the Sales workbook is shared with can open it.',
		)
		const both = item('b', 'P7', {
			workbook: 'Sales',
			users: [ALICE, BOB],
			shared: ['chart', 'dashboard'],
			removed: [
				{ kind: 'chart', title: 'Revenue', write: true },
				{ kind: 'dashboard', title: 'Overview', write: false },
			],
		})
		expect(text(sentenceOf(both, DAVE).text)).toBe(
			'Alice and Bob can now open the whole Sales workbook, as some of its charts and dashboards were shared with them. ' +
				'Everyone could edit the Revenue chart and open the Overview dashboard. Those shares are gone, so only people the Sales workbook is shared with can open them.',
		)
	})

	// @feature upgrade.item-sentences
	it('asks for what lets a public chart run as its owner again', () => {
		const chart = { chart: 'Public revenue', owner: BOB }
		const disabled = sentenceOf(
			item('a', 'P12', { ...chart, reason: 'disabled' }, { form_url: '/desk/user/bob' }),
			DAVE,
		)
		expect(text(disabled.todo)).toBe('Enable Bob so guests see it again.')
		expect(disabled.action).toEqual({
			kind: 'form',
			label: 'Open Bob’s user',
			url: '/desk/user/bob',
		})
		const noRole = sentenceOf(item('b', 'P12', { ...chart, reason: 'no_insights_role' }), DAVE)
		expect(text(noRole.todo)).toBe('Give Bob an Insights role so guests see it again.')
		const cannotEdit = sentenceOf(
			item('c', 'P12', { ...chart, reason: 'cannot_edit' }, { workbook: '25' }),
			DAVE,
		)
		expect(text(cannotEdit.todo)).toBe('Share the workbook with Bob to edit.')
		expect(cannotEdit.action).toMatchObject({ kind: 'route', label: 'Open workbook sharing' })
	})

	// @feature upgrade.item-sentences
	it('opens what an admin-only script lives in, by its kind', () => {
		const data = { title: 'Script rows', author: ALICE }
		const onChart = {
			reference_doctype: 'Insights Chart v3',
			reference_name: 'c1',
			workbook: '9',
		}
		const onAlert = { reference_doctype: 'Insights Alert', form_url: '/desk/insights-alert/a1' }
		expect(sentenceOf(item('a', 'P20', data, onChart), DAVE).action?.label).toBe('Open chart')
		expect(sentenceOf(item('b', 'P20', data, onAlert), DAVE).action?.label).toBe('Open alert')
		expect(text(sentenceOf(item('c', 'P20', data), DAVE).text)).toBe(
			'Only admins can edit Alice’s Script rows script now. It still runs.',
		)
	})

	// @feature upgrade.item-sentences
	it('says who an alert runs as now, or why it will stop', () => {
		const alert = { alert: 'Low stock' }
		const moved = sentenceOf(
			item('a', 'P19', { ...alert, outcome: 'moved', owner: ALICE, enabler: BOB }),
			DAVE,
		)
		expect(text(moved.text)).toBe(
			'The Low stock alert now runs as Alice, who owns its workbook, in place of Bob.',
		)
		expect(moved.todo).toBeUndefined()
		expect(
			text(sentenceOf(item('b', 'P19', { ...alert, outcome: 'no_user' }), DAVE).text),
		).toBe('The Low stock alert has no one to run as, so it will stop.')
		const stops = sentenceOf(
			item('c', 'P19', { ...alert, outcome: 'stops', enabler: BOB }),
			DAVE,
		)
		expect(text(stops.text)).toBe(
			'The Low stock alert will stop, because Bob can’t edit its workbook.',
		)
		expect(text(stops.todo)).toBe('Share the workbook with Bob to edit.')
	})

	// @feature upgrade.item-sentences
	it('says which setting a number reads differently and how to set it again', () => {
		const cases: [string, Record<string, any>, string, string][] = [
			[
				'K1',
				{ dashboard: 'Sales', start: '2024-01-01', end: '2024-03-31' },
				'The Sales dashboard lost its default date range (2024-01-01 – 2024-03-31), which earlier releases showed but never applied.',
				'Set it again if you want it.',
			],
			[
				'N4',
				{ chart: 'Revenue' },
				'The Revenue number card lost its currency sign.',
				'Add the sign to the card’s suffix.',
			],
			[
				'N6',
				{ chart: 'Revenue' },
				'The Revenue number card now shows a total of all rows.',
				'Pick a Date column to show a period.',
			],
			[
				'Q13',
				{ start: '2024-04-01' },
				'Fiscal years now start on 1 April, from ERPNext’s current fiscal year.',
				'Set Fiscal Year Start to choose.',
			],
		]
		for (const [code, data, said, todo] of cases) {
			const sentence = sentenceOf(item('a', code, data), DAVE, 'en-GB')
			expect(text(sentence.text)).toBe(said)
			expect(text(sentence.todo)).toBe(todo)
		}
		const settings = sentenceOf(
			item('b', 'Q13', { start: '2024-04-01' }, { action: 'open_settings' }),
			DAVE,
		)
		expect(settings.action).toEqual({ kind: 'fix', label: 'Open settings' })

		const copy = { workbook: 'Sales Performance', standard: 'Selling', app: 'ERPNext' }
		const changed = sentenceOf(item('c', 'W2', copy, { workbook: 'wb' }), DAVE)
		expect(text(changed.text)).toBe(
			'The Sales Performance workbook is a copy of an old Insights template. ERPNext’s Selling workbook replaces it and gets updates.',
		)
		expect(text(changed.todo)).toBe(
			'Move what you changed to the Selling workbook, then delete the copy.',
		)
		expect(changed.action).toMatchObject({ kind: 'route', label: 'Open workbook' })
		const untouched = sentenceOf(item('d', 'W2', copy, { action: 'delete_workbook' }), DAVE)
		expect(text(untouched.todo)).toBe('The copy was never changed, so delete it.')
		expect(untouched.action).toEqual({ kind: 'fix', label: 'Delete copy' })
	})

	// @feature upgrade.item-sentences
	it('names what a detail item is about', () => {
		const cases: [string, Record<string, any>, string][] = [
			[
				'N5',
				{ chart: 'Revenue', column: 'Posting Date' },
				'The Revenue number card now shows the total of the latest day of Posting Date.',
			],
			[
				'J1',
				{ alert: 'Watch a cache', chart: 'Revenue' },
				'The Watch a cache alert checks a saved copy of the Revenue chart. Changes to the chart don’t reach it.',
			],
			[
				'P21',
				{ query: 'Origin script', workbook: 'Reader', variables: ['api_token'] },
				'The Origin script script was copied into the Reader workbook without its secret api_token. It won’t run until someone enters it.',
			],
			[
				'P21',
				{ cycle: true, query: 'A', workbook: 'Sales', source: 'B' },
				'The A query in the Sales workbook reads the B query, which reads it back. Remove that source.',
			],
		]
		for (const [code, data, said] of cases) {
			expect(text(sentenceOf(item('a', code, data), DAVE).text)).toBe(said)
		}
	})

	// @feature upgrade.item-sentences
	it('falls back to the stored message for an item written before it had data', () => {
		const old = item('a', 'P17', {})
		expect(text(sentenceOf(old, DAVE).text)).toBe('P17 message')
	})

	// @feature upgrade.item-sentences
	it('opens a desk form in a new tab, and a workbook at its share dialog', () => {
		const access = item(
			'a',
			'P17',
			{ user: BOB, doctypes: ['Customer'] },
			{ form_url: '/desk/user/bob' },
		)
		expect(sentenceOf(access, DAVE).action).toEqual({
			kind: 'form',
			label: 'Open Bob’s roles',
			url: '/desk/user/bob',
		})
		const shared = item('b', 'P3', { workbook: 'Sales', users: [BOB] }, { workbook: '25' })
		expect(sentenceOf(shared, DAVE).action).toEqual({
			kind: 'route',
			label: 'Open workbook sharing',
			route: { name: 'Workbook', params: { workbook_name: '25' }, query: { share: '1' } },
		})
	})
})

describe('a desk link in an item', () => {
	// @feature upgrade.desk-links
	it('is offered only where the server names the page, for a reader who may make the fix there', () => {
		const items = (form_url: string | null) => [
			item('a', 'P17', { user: BOB, doctypes: ['Customer'] }, { form_url }),
			item(
				'b',
				'P17',
				{
					team: 'North',
					members: [BOB],
					restrictions: [{ doctype: 'Customer', field: 'territory', value: 'North' }],
				},
				{ form_url },
			),
			item(
				'c',
				'P12',
				{ chart: 'Public revenue', owner: BOB, reason: 'disabled' },
				{ form_url },
			),
		]
		const offered = items('/desk/x').map((each) => sentenceOf(each, DAVE).action?.label)
		expect(offered).toEqual(['Open Bob’s roles', 'Open User Permissions', 'Open Bob’s user'])

		const withheld = items(null).map((each) => sentenceOf(each, DAVE).action)
		expect(withheld).toEqual([undefined, undefined, undefined])
	})
})

describe('the sidebar card', () => {
	// @feature upgrade.wizard
	it('counts the open items, whatever step the wizard was left at', () => {
		expect(cardDescription(14, { index: 5, count: 6 })).toBe('14 items to review')
		expect(cardDescription(1)).toBe('1 item to review')
	})

	// @feature upgrade.wizard
	it('names the step only when no item is open', () => {
		expect(cardDescription(0, { index: 1, count: 3 })).toBe('Step 2 of 3')
		expect(cardDescription(0)).toBe('All done')
	})
})

describe('the badge of a step', () => {
	// @feature upgrade.wizard
	it('says a step that only tells has items to read, until they are read', () => {
		expect(stepBadge(3, 'note')).toEqual({ theme: 'gray', label: 'To read' })
		expect(stepBadge(2, 'now')).toEqual({ theme: 'amber', label: 'Needs you now' })
		expect(stepBadge(0, 'note')).toEqual({ theme: 'green', label: 'Done' })
	})
})

describe('a key in the wizard', () => {
	const at = (focus: Partial<Parameters<typeof keyAction>[1]> = {}) => ({
		inField: false,
		onControl: false,
		hasNext: false,
		...focus,
	})

	// @feature upgrade.wizard
	it('goes back with ←, and pages with → only while an item follows', () => {
		expect(keyAction('ArrowLeft', at())).toBe('back')
		expect(keyAction('ArrowRight', at({ hasNext: true }))).toBe('next')
		expect(keyAction('ArrowRight', at())).toBeUndefined()
	})

	// @feature upgrade.wizard
	it('presses the primary button with Enter, unless another control has focus', () => {
		expect(keyAction('Enter', at())).toBe('primary')
		expect(keyAction('Enter', at({ onControl: true }))).toBeUndefined()
	})

	// @feature upgrade.wizard
	it('leaves typing in a field alone', () => {
		for (const key of ['ArrowLeft', 'ArrowRight', 'Enter']) {
			expect(keyAction(key, at({ inField: true, hasNext: true }))).toBeUndefined()
		}
	})
})

describe('the item a step shows', () => {
	const rows = ['a', 'b', 'c', 'd'].map((name) => ({ item: item(name, 'P10'), names: [name] }))
	const doneOf =
		(...names: string[]) =>
		(row: (typeof rows)[number]) =>
			names.includes(row.item.name)

	// @feature upgrade.wizard
	it('opens on the first open item, or the last when all are done', () => {
		expect(startIndex(rows, doneOf('a', 'b'))).toBe(2)
		expect(startIndex(rows, doneOf('a', 'b', 'c', 'd'))).toBe(3)
	})

	// @feature upgrade.wizard
	it('moves on after Done to the next open item, going round to the first', () => {
		expect(nextOpenIndex(rows, 1, doneOf('b', 'c'))).toBe(3)
		expect(nextOpenIndex(rows, 3, doneOf('b', 'c', 'd'))).toBe(0)
		expect(nextOpenIndex(rows, 2, doneOf('a', 'b', 'c', 'd'))).toBe(2)
	})
})

describe('the picture beside a wizard page', () => {
	async function drawn(name: PictureName) {
		const app = createSSRApp({
			render: () =>
				h(UpgradePicture, { name, person: { full_name: 'Bob Fixture', email: BOB } }),
		})
		app.config.warnHandler = () => {}
		const html = await renderToString(app)
		// the frame holds no element when no branch draws the name
		return html
			.slice(html.indexOf('>') + 1, html.lastIndexOf('</div>'))
			.replace(/<!--.*?-->/g, '')
	}

	// @feature upgrade.wizard
	it('draws every picture a page can name', async () => {
		for (const name of PICTURES) {
			expect(await drawn(name), name).not.toBe('')
		}
	})
})
