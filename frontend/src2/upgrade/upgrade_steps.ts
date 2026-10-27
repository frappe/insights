import { __, translatedTable } from '../translation'
import type { UpgradeItem } from './upgrade'

/** A run of a sentence: plain, or a name the reader scans for. */
export type Part = { text: string; em?: boolean }

/** Where an item's button takes the reader. */
export type ItemAction =
	| { kind: 'form'; label: string; url: string }
	| { kind: 'route'; label: string; route: Record<string, any> }
	| { kind: 'fix'; label: string }

/** What an item says: what happened, what to do about it, and the button that does it. */
export type Sentence = { text: Part[]; todo?: Part[]; action?: ItemAction }

/** The items about one thing. An admin gets both sides of a change that told two people. */
export type Row = { item: UpgradeItem; names: string[] }

export const PICTURES = [
	'charts',
	'appDashboards',
	'showInDesk',
	'drill',
	'roles',
	'notPermitted',
	'shareBefore',
	'shareNow',
	'runAsOwner',
	'workbookAccess',
	'chartOwner',
	'numberCards',
] as const

export type PictureName = (typeof PICTURES)[number]

/** What a feature page needs of the reader: the server says whether they have it. */
export type Can = { readStandardDashboards: boolean; showInDesk: boolean; share: boolean }

/** One thing a reader upgrading to Insights v3.50 gains, on a page of its own. */
export type Feature = {
	id: string
	label: string
	title: string
	/** What the reader gets: a bold lead clause, then the detail. */
	lead: [string, string]
	/** An aside the title's info button opens, with a link to the release notes. */
	info?: string
	picture?: PictureName
	needs?: keyof Can
}

// What a reader upgrading to Insights v3.50 gains, most visible first. Sharing has a
// page of its own design, before and now, and leads into the upgrade steps.
export const features = translatedTable<Feature[]>(() => [
	{
		id: 'charts',
		label: __('Charts'),
		title: __('Charts, rebuilt'),
		lead: [
			__('Every chart is redrawn on frappe-ui charts,'),
			__('with dark mode, a Heatmap, trend lines and Number cards that track a target.'),
		],
		info: __('A few numbers change because earlier releases computed them wrongly.'),
		picture: 'charts',
	},
	{
		id: 'drill',
		label: __('Drill Downs'),
		title: __('Click a chart for its rows'),
		lead: [
			__('Click any bar to see the rows behind it,'),
			__('or break it down by another column.'),
		],
		picture: 'drill',
	},
	{
		id: 'standard',
		label: __('App Dashboards'),
		title: __('Dashboards from ERPNext and Frappe HR'),
		lead: [
			__('Selling, Stock, Accounts, Payroll and more come ready to use.'),
			__('Duplicate one to change it.'),
		],
		picture: 'appDashboards',
		needs: 'readStandardDashboards',
	},
	{
		id: 'desk',
		label: __('Desk Charts'),
		title: __('Charts on desk workspaces'),
		lead: [
			__('Pick Show in Desk on a chart'),
			__('to put it on a desk dashboard or workspace.'),
		],
		picture: 'showInDesk',
		needs: 'showInDesk',
	},
	{
		id: 'sharing',
		label: __('Sharing'),
		title: __('Share the workbook, not the chart'),
		lead: [
			__('People edit through the workbook.'),
			__('Sharing a chart or dashboard only lets them read it.'),
		],
		needs: 'share',
	},
	{
		id: 'roles',
		label: __('Desk Roles'),
		title: __('Share dashboards with desk roles'),
		lead: [
			__('Anyone with those roles can open the dashboard,'),
			__('even without an Insights role.'),
		],
		picture: 'roles',
		needs: 'share',
	},
])

/** The feature pages of what the reader can do. */
export function featuresFor(can: Can): Feature[] {
	return features().filter((feature) => !feature.needs || can[feature.needs])
}

/** What a wizard step is about. `now` asks for a decision, `note` only tells. */
export type Group = {
	id: string
	label: string
	kind: 'now' | 'note'
	codes: string[]
	title: string
	/** What changed: a bold lead clause, then the detail. */
	lead: [string, string]
	picture?: PictureName
}

/** The headings the nav groups the steps under; the welcome has none. */
export const sections = translatedTable<Record<Step['section'], string | undefined>>(() => ({
	welcome: undefined,
	new: __("What's New"),
	upgrade: __('Your Upgrade'),
}))

export type Step =
	| { id: 'welcome'; label: string; section: 'welcome' }
	| { id: string; label: string; section: 'new'; feature: Feature }
	| { id: string; label: string; section: 'upgrade'; group: Group; rows: Row[] }

// The order an admin works through them: who sees which data, then who may
// open what, then what stops, then what reads other numbers, then what only
// tells.
export const groups = translatedTable<Group[]>(() => [
	{
		id: 'access',
		label: __('Access'),
		kind: 'now',
		codes: ['P17'],
		title: __('Some people now see Not Permitted'),
		lead: [
			__('Site data now follows desk permissions,'),
			__('so Insights teams no longer give anyone rows.'),
		],
		picture: 'notPermitted',
	},
	{
		id: 'public',
		label: __('Public Charts'),
		kind: 'now',
		codes: ['P10', 'P12'],
		title: __('Public charts run as their owner'),
		lead: [
			__('Public charts now run as their owner,'),
			__('so everyone who opens one sees what the owner can read.'),
		],
		picture: 'runAsOwner',
	},
	{
		id: 'workbooks',
		label: __('Workbook Access'),
		kind: 'now',
		codes: ['P7', 'P3', 'P4'],
		title: __('Some people can open or edit more, or less'),
		lead: [
			__('Access now comes from the workbook,'),
			__('so some people gained or lost whole workbooks.'),
		],
		picture: 'workbookAccess',
	},
	{
		id: 'alerts',
		label: __('Alerts'),
		kind: 'now',
		codes: ['P19'],
		title: __('Some alerts run as someone else, or will stop'),
		lead: [
			__('An alert now runs as someone who can edit its workbook,'),
			__('so some moved to the workbook’s owner and some will stop.'),
		],
		picture: 'workbookAccess',
	},
	{
		id: 'numbers',
		label: __('Numbers'),
		kind: 'now',
		codes: ['K1', 'N4', 'N6', 'Q13'],
		title: __('Some numbers need a setting again'),
		lead: [
			__('Insights v3.50 reads a few settings differently,'),
			__('so these show other numbers until you set them again.'),
		],
		picture: 'numberCards',
	},
	{
		id: 'copies',
		label: __('Template Copies'),
		kind: 'now',
		codes: ['W2'],
		title: __('Some workbooks are copies of a shipped dashboard'),
		lead: [
			__('ERPNext and Frappe HR now ship dashboards,'),
			__('so copies of their templates get no updates.'),
		],
		picture: 'appDashboards',
	},
	{
		id: 'notes',
		label: __('Good to Know'),
		kind: 'note',
		codes: ['P11'],
		title: __('Public charts moved to who published them'),
		lead: [
			__('Each now belongs to the person who published it,'),
			__('so its readers keep seeing the same rows.'),
		],
		picture: 'chartOwner',
	},
])

// The Good to know step when it holds more than moved charts: the reader's items
// outside the groups. An admin's also hold those addressed to no one, such as
// changes to Administrator's work, so they are not all the admin's own.
const yourNotes = translatedTable<Pick<Group, 'title' | 'lead'>>(() => ({
	title: __('A few changes to what you made'),
	lead: [__('The upgrade changed some of your work,'), __('and each change says what it means.')],
}))
const adminNotes = translatedTable<Pick<Group, 'title' | 'lead'>>(() => ({
	title: __('A few more changes'),
	lead: [
		__('The upgrade changed some work no other step covers,'),
		__('and each change says what it means.'),
	],
}))

// Items outside the groups that tell of something failing until someone acts: a script or
// import that will fail, a script without its secret.
const FAILURES = new Set(['P21', 'Q1', 'J4', 'Q5'])

/**
 * Whether an item needs its reader: its group asks for a decision, or it tells
 * of a failure, as a moved chart whose publisher is disabled does.
 */
export function needsYou(item: UpgradeItem): boolean {
	if (FAILURES.has(item.code) || (item.code === 'P11' && item.data?.publisher_disabled)) {
		return true
	}
	return groups().some((group) => group.kind === 'now' && group.codes.includes(item.code))
}

/**
 * What a step's badge says. A step that only tells still counts its items until
 * the reader has read them, so it says so rather than that nothing is left.
 */
export function stepBadge(
	open: number,
	kind: Group['kind'],
): { theme: 'green' | 'amber' | 'gray'; label: string } {
	if (!open) return { theme: 'green', label: __('Done') }
	return kind === 'now'
		? { theme: 'amber', label: __('Needs you now') }
		: { theme: 'gray', label: __('To read') }
}

/**
 * What the sidebar card says: the items left while any is open, else the step
 * the wizard was left at, else that it is done.
 */
export function cardDescription(left: number, step?: { index: number; count: number }): string {
	if (left === 1) return __('1 item to review')
	if (left) return __('{0} items to review', String(left))
	if (step) return __('Step {0} of {1}', String(step.index + 1), String(step.count))
	return __('All done')
}

/** The picture of the group an item belongs to, which a step of mixed items shows while it is current. */
export function pictureOf(item: UpgradeItem): PictureName | undefined {
	return groups().find((group) => group.codes.includes(item.code))?.picture
}

/** One row per thing. Two items with the same code, reference and data say the same sentence. */
export function rowsOf(items: UpgradeItem[]): Row[] {
	const rows = new Map<string, Row>()
	for (const item of items) {
		const key = JSON.stringify([
			item.code,
			item.reference_doctype,
			item.reference_name,
			item.data ?? {},
		])
		const row = rows.get(key)
		if (row) row.names.push(item.name)
		else rows.set(key, { item, names: [item.name] })
	}
	return [...rows.values()]
}

/**
 * The wizard's steps for this reader. A step with nothing in it is left out,
 * and items outside the groups go to Good to know. Every item lands in one row,
 * so the sidebar card counts what the server counts. The server sends only the
 * items the reader works through: an admin gets no note addressed to someone
 * else (`item_filters`).
 */
export function wizardSteps(
	items: UpgradeItem[],
	options: { can: Can; admin: boolean; me: string },
): Step[] {
	const steps: Step[] = [{ id: 'welcome', label: __('Welcome'), section: 'welcome' }]
	for (const feature of featuresFor(options.can)) {
		steps.push({ id: feature.id, label: feature.label, section: 'new', feature })
	}
	const inSteps = new Set(groups().flatMap((group) => group.codes))
	for (const group of groups()) {
		const codes =
			group.kind === 'note'
				? [
						...group.codes,
						...items.map((item) => item.code).filter((code) => !inSteps.has(code)),
				  ]
				: group.codes
		const rows = rowsOf(items.filter((item) => codes.includes(item.code)))
		if (!rows.length) continue
		const mixed = rows.some((row) => !group.codes.includes(row.item.code))
		// a step asks for the reader when any of its items does
		const kind = rows.some((row) => needsYou(row.item)) ? 'now' : 'note'
		steps.push({
			id: group.id,
			label: group.label,
			section: 'upgrade',
			group: mixed
				? // each item shows its own group's picture, if it has one
				  {
						...group,
						...(options.admin ? adminNotes() : yourNotes()),
						codes,
						kind,
						picture: undefined,
				  }
				: { ...group, kind },
			rows,
		})
	}
	return steps
}

/**
 * Where the wizard opens for a stored step id. A step the reader no longer
 * gets is gone, and the reader goes on to the step after it.
 */
export function stepIndexOf(steps: Step[], id: string): number {
	const order = [
		'welcome',
		...features().map((feature) => feature.id),
		...groups().map((group) => group.id),
	]
	const at = order.indexOf(id)
	const index = steps.findIndex((step) => order.indexOf(step.id) >= at)
	return index < 0 ? steps.length - 1 : index
}

/**
 * What a key does in the wizard. ← goes back on every step, → pages a step's
 * items, and Enter presses the screen's primary button unless
 * focus is on another control, which Enter presses itself. Typing in a field is
 * left alone.
 */
export function keyAction(
	key: string,
	focus: { inField: boolean; onControl: boolean; hasNext: boolean },
): 'back' | 'next' | 'primary' | undefined {
	if (focus.inField) return
	if (key === 'ArrowLeft') return 'back'
	if (key === 'ArrowRight' && focus.hasNext) return 'next'
	if (key === 'Enter' && !focus.onControl) return 'primary'
}

/** The row a step opens on: its first open one, else its last. */
export function startIndex(rows: Row[], isDone: (row: Row) => boolean): number {
	const open = rows.findIndex((row) => !isDone(row))
	return open === -1 ? rows.length - 1 : open
}

/** The next open row after `from`, going round to the first; `from` when none is. */
export function nextOpenIndex(rows: Row[], from: number, isDone: (row: Row) => boolean): number {
	for (let offset = 1; offset < rows.length; offset++) {
		const index = (from + offset) % rows.length
		if (!isDone(rows[index])) return index
	}
	return from
}

// ---------- sentences ----------

/**
 * A translated template with its names put in. `{0}`, `{1}`… take the parts in
 * order, so a translation may move a name.
 */
export function say(template: string, ...args: (Part | Part[])[]): Part[] {
	const parts: Part[] = []
	for (const [index, piece] of template.split(/{(\d+)}/).entries()) {
		if (index % 2 === 0) {
			if (piece) parts.push({ text: piece })
		} else {
			const arg = args[Number(piece)]
			parts.push(...(Array.isArray(arg) ? arg : arg ? [arg] : []))
		}
	}
	return parts
}

const em = (text: string): Part => ({ text, em: true })
type Kind =
	| 'workbook'
	| 'chart'
	| 'number card'
	| 'dashboard'
	| 'query'
	| 'script'
	| 'alert'
	| 'import job'

/**
 * What a name is, then the name: workbook **Sales**. The kind leads, so a title
 * that reads like a sentence does not swallow it.
 */
function titled(kind: Kind, title: string): Part[] {
	const template = {
		workbook: __('workbook {0}'),
		chart: __('chart {0}'),
		'number card': __('number card {0}'),
		dashboard: __('dashboard {0}'),
		query: __('query {0}'),
		script: __('script {0}'),
		alert: __('alert {0}'),
		'import job': __('import job {0}'),
	}[kind]
	return say(template, em(title))
}

/** "a, b and c", or "a, b, c and 2 more" past `limit`. */
export function listOf(names: string[], limit = Infinity): string {
	const shown =
		names.length > limit
			? [...names.slice(0, limit), __('{0} more', String(names.length - limit))]
			: names
	if (shown.length < 2) return shown.join('')
	return __('{0} and {1}', shown.slice(0, -1).join(', '), shown[shown.length - 1])
}

/** Runs of a sentence read as a list: "a, b and c". */
function joined(items: Part[][]): Part[] {
	if (items.length < 2) return items[0] ?? []
	const head = items
		.slice(0, -1)
		.flatMap((part, index) => (index ? [{ text: ', ' }, ...part] : part))
	return say(__('{0} and {1}'), head, items[items.length - 1])
}

/** A doctype read as a set of documents: Sales Invoices. English only, where a plural is a suffix. */
function documents(doctype: string): string {
	const label = __(doctype)
	if (label !== doctype) return label
	if (/[^aeiou]y$/.test(doctype)) return `${doctype.slice(0, -1)}ies`
	if (/(s|x|ch|sh)$/.test(doctype)) return `${doctype}es`
	return `${doctype}s`
}

/** Who a sentence is about, as the reader knows them: "you", or their first name. */
export type People = {
	me: string
	name: (user: string) => string
}

export function peopleFor(item: UpgradeItem, me: string): People {
	return {
		me,
		name: (user) => item.people?.[user]?.first_name || item.people?.[user]?.full_name || user,
	}
}

function person(people: People, user: string, start = false) {
	if (user === people.me) return start ? __('You') : __('you')
	return people.name(user)
}

function possessive(people: People, user: string) {
	return user === people.me ? __('your') : __('{0}’s', people.name(user))
}

function names(people: People, users: string[], start = false) {
	return listOf(users.map((user, index) => person(people, user, start && index === 0)))
}

function formatDay(iso: string, locale: string) {
	const date = new Date(`${iso}T00:00:00`)
	if (Number.isNaN(date.getTime())) return iso
	return date.toLocaleDateString(locale || undefined, { day: 'numeric', month: 'long' })
}

/** Where an item that names a document in the app opens it: a route in its workbook. */
function routeTo(item: UpgradeItem, label: string, query?: Record<string, string>) {
	if (!item.workbook) return formAction(item, label)
	const doctype = item.reference_doctype
	const name = item.reference_name
	const params: Record<string, string> = { workbook_name: item.workbook }
	let routeName = 'Workbook'
	if (doctype === 'Insights Query v3') [routeName, params.query_name] = ['WorkbookQuery', name!]
	if (doctype === 'Insights Chart v3') [routeName, params.chart_name] = ['WorkbookChart', name!]
	if (doctype === 'Insights Dashboard v3') {
		;[routeName, params.dashboard_name] = ['WorkbookDashboard', name!]
	}
	return {
		kind: 'route' as const,
		label,
		route: { name: routeName, params, ...(query ? { query } : {}) },
	}
}

function formAction(item: UpgradeItem, label: string): ItemAction | undefined {
	return item.form_url ? { kind: 'form', label, url: item.form_url } : undefined
}

function workbookSharing(item: UpgradeItem, label: string): ItemAction | undefined {
	if (!item.workbook) return undefined
	return {
		kind: 'route',
		label,
		route: {
			name: 'Workbook',
			params: { workbook_name: item.workbook },
			query: { share: '1' },
		},
	}
}

/** What an item says to `me`, built from the names the patch stored on it. */
export function sentenceOf(item: UpgradeItem, me: string, locale = 'en-US'): Sentence {
	const d = item.data ?? {}
	const people = peopleFor(item, me)
	const build = SENTENCES[item.code]
	const built = build && hasData(d) ? build(item, d, people, locale) : undefined
	if (built) return built
	return { text: [{ text: item.message }], action: routeTo(item, __('Open')) }
}

function hasData(data: Record<string, any>) {
	return Object.keys(data).length > 0
}

type Build = (
	item: UpgradeItem,
	d: Record<string, any>,
	people: People,
	locale: string,
) => Sentence | undefined

const SENTENCES: Partial<Record<string, Build>> = {
	P17(item, d, people) {
		if (d.user) {
			const unreadable = listOf((d.doctypes ?? []).map(documents), 3)
			const narrowed = listOf((d.narrowed ?? []).map(documents), 3)
			const self = d.user === people.me
			const who = em(person(people, d.user, true))
			let text: Part[]
			if (unreadable && narrowed) {
				text = self
					? say(
							__(
								'You can’t see charts on {0} any more, and see only the rows desk gives you of {1}.',
							),
							em(unreadable),
							em(narrowed),
					  )
					: say(
							__(
								'{0} can’t see charts on {1} any more, and sees only the rows desk gives them of {2}.',
							),
							who,
							em(unreadable),
							em(narrowed),
					  )
			} else if (unreadable) {
				text = say(__('{0} can’t see charts on {1} any more.'), who, em(unreadable))
			} else {
				text = self
					? say(__('You now see only the rows desk gives you of {0}.'), em(narrowed))
					: say(
							__('{0} now sees only the rows desk gives them of {1}.'),
							who,
							em(narrowed),
					  )
			}
			return {
				text,
				// a role lets them read a doctype again; rows desk narrows are its rule to keep
				todo: !unreadable
					? self
						? say(
								__(
									'If you need more rows, ask for a desk role or User Permission that gives them.',
								),
						  )
						: say(
								__(
									'If {0} needs more rows, give them a desk role or User Permission that does.',
								),
								{
									text: people.name(d.user),
								},
						  )
					: self
					  ? say(__('Give yourself a desk role that can read them.'))
					  : say(__('Give {0} a desk role that can read them.'), {
								text: people.name(d.user),
					    }),
				action: formAction(
					item,
					self ? __('Open your roles') : __('Open {0}’s roles', people.name(d.user)),
				),
			}
		}
		if (d.team) {
			const restrictions: Record<string, any>[] = d.restrictions ?? []
			const limits = restrictions.map((restriction) => [
				em(documents(restriction.doctype ?? '')),
				{ text: ' ' },
				...(restriction.field !== undefined
					? say(
							__('where {0} is {1}'),
							{ text: String(restriction.field).replace(/_/g, ' ') },
							em(String(restriction.value)),
					  )
					: say(__('where {0}'), em(String(restriction.condition ?? '')))),
			])
			return {
				text: say(
					restrictions.length > 1
						? __('The {0} limited {1} to {2}. Those rules no longer apply.')
						: __('The {0} limited {1} to {2}. That rule no longer applies.'),
					em(d.team),
					em(names(people, d.members ?? [])),
					joined(limits),
				),
				todo: say(__('Set a User Permission in desk instead.')),
				action: formAction(item, __('Open User Permissions')),
			}
		}
	},
	P10(item, d, people) {
		if (d.reason === 'unreadable') {
			return {
				text: say(
					__(
						'The {0} runs as {1}, who can’t read {2}, so everyone who opens it sees Not Permitted.',
					),
					titled('chart', d.chart),
					em(person(people, d.owner)),
					tablesOf(d.doctypes),
				),
				...giveReadAccess(item, people, d.owner, d.doctypes),
			}
		}
		const rows =
			d.reason === 'script' || !d.table
				? em(__('{0} rows', possessive(people, d.owner)))
				: em(`${possessive(people, d.owner)} ${documents(d.table)}`)
		return {
			text: say(
				__('Everyone who opens the {0} now sees {1}, not their own.'),
				titled('chart', d.chart),
				rows,
			),
			todo: say(
				__(
					'If each reader should see their own rows, turn off Run as owner in its sharing.',
				),
			),
			action: routeTo(item, __('Open sharing'), { share: '1' }),
		}
	},
	P12(item, d, people) {
		const owner = em(person(people, d.owner))
		const text =
			d.reason === 'disabled'
				? say(
						__('The {0} can’t run as {1}, who is disabled, so guests see nothing.'),
						titled('chart', d.chart),
						owner,
				  )
				: d.reason === 'no_insights_role'
				  ? say(
							__(
								'The {0} can’t run as {1}, who has no Insights role, so guests see nothing.',
							),
							titled('chart', d.chart),
							owner,
				    )
				  : say(
							__('The {0} can’t run as {1} any more, so guests see nothing.'),
							titled('chart', d.chart),
							owner,
				    )
		// what lets the chart run as its owner again: the owner back, a role, or edit access
		const ownerName = { text: person(people, d.owner) }
		if (d.reason === 'disabled' || d.reason === 'no_insights_role') {
			return {
				text,
				todo:
					d.reason === 'disabled'
						? say(__('Enable {0} so guests see it again.'), ownerName)
						: say(__('Give {0} an Insights role so guests see it again.'), ownerName),
				action: formAction(
					item,
					d.owner === people.me
						? __('Open your user')
						: __('Open {0}’s user', people.name(d.owner)),
				),
			}
		}
		return {
			text,
			todo: say(__('Share the workbook with {0} to edit.'), ownerName),
			action: workbookSharing(item, __('Open workbook sharing')),
		}
	},
	P7(item, d, people) {
		const removed: { kind: 'chart' | 'dashboard' | 'query'; title: string; write: boolean }[] =
			d.removed ?? []
		const users: string[] = d.users ?? []
		const text: Part[] = []
		if (users.length) {
			text.push(
				...say(
					__('{0} can now open the whole {1}, as some of its {2} were shared with them.'),
					em(names(people, users, true)),
					titled('workbook', d.workbook),
					{ text: listOf((d.shared ?? []).map(memberKinds)) },
				),
			)
		}
		if (removed.length) {
			const shares = removed.map((share) =>
				say(
					share.write ? __('edit the {0}') : __('open the {0}'),
					titled(share.kind, share.title),
				),
			)
			if (text.length) text.push({ text: ' ' })
			text.push(
				...say(
					removed.length > 1
						? __(
								'Everyone could {0}. Those shares are gone, so only people the {1} is shared with can open them.',
						  )
						: __(
								'Everyone could {0}. That share is gone, so only people the {1} is shared with can open it.',
						  ),
					joined(shares),
					titled('workbook', d.workbook),
				),
			)
		}
		return {
			text,
			todo: removed.length
				? say(__('Share the workbook with whoever still needs them.'))
				: say(__('Remove anyone from its sharing who should not open all of it.')),
			action: workbookSharing(item, __('Open workbook sharing')),
		}
	},
	P3(item, d, people) {
		const users: string[] = d.users ?? []
		const one = users.length === 1
		return {
			text: say(
				one
					? __('{0} can now edit the whole {1}, because they made something in it.')
					: __('{0} can now edit the whole {1}, because each made something in it.'),
				em(names(people, users, true)),
				titled('workbook', d.workbook),
			),
			todo: one
				? say(__('If {0} should only read it, change their access in its sharing.'), {
						text: person(people, users[0]),
				  })
				: say(
						__(
							'If any of them should only read it, change their access in its sharing.',
						),
				  ),
			action: workbookSharing(item, __('Open workbook sharing')),
		}
	},
	P4(item, d, people) {
		const users: string[] = d.users ?? []
		const teams: string[] = d.teams ?? []
		// the patch keeps titles only, not whether each is a chart, dashboard or query
		const titles = (d.items ?? []).map((title: string) => em(title))
		const itemParts =
			titles.length < 2
				? titles
				: say(
						__('{0} and {1}'),
						titles
							.slice(0, -1)
							.flatMap((part: Part, index: number) =>
								index ? [{ text: ', ' }, part] : [part],
							),
						titles[titles.length - 1],
				  )
		return {
			text: say(
				__(
					'{0} edited {1} through the {2}. Teams only give read access now, so {3} can’t edit them.',
				),
				em(names(people, users, true)),
				itemParts,
				em(listOf(teams)),
				{ text: users.length === 1 ? person(people, users[0]) : __('they') },
			),
			todo:
				users.length === 1
					? say(__('Share the workbook with {0} to edit, if they still need to.'), {
							text: person(people, users[0]),
					  })
					: say(__('Share the workbook to edit with whoever still needs to.')),
			action: workbookSharing(
				item,
				users.length === 1
					? __('Share the workbook with {0}', person(people, users[0]))
					: __('Open workbook sharing'),
			),
		}
	},
	P19(item, d, people) {
		const alert = titled('alert', d.alert)
		if (!d.enabler) {
			return {
				text: say(__('The {0} has no one to run as, so it will stop.'), alert),
				// turning an alert on makes it run as whoever turned it on
				todo: say(__('Turn it off and on again as someone who can edit its workbook.')),
				action: workbookSharing(item, __('Open workbook sharing')),
			}
		}
		return {
			text: say(
				__('The {0} will stop, because {1} can’t edit its workbook.'),
				alert,
				em(person(people, d.enabler)),
			),
			todo: say(__('Share the workbook with {0} to edit.'), {
				text: person(people, d.enabler),
			}),
			action: workbookSharing(item, __('Open workbook sharing')),
		}
	},
	K1(item, d) {
		return {
			text: say(
				__(
					'The {0} lost its default date range ({1}), which earlier releases showed but never applied.',
				),
				titled('dashboard', d.dashboard),
				{ text: `${d.start} – ${d.end}` },
			),
			todo: say(__('Set it again if you want it.')),
			action: routeTo(item, __('Open dashboard')),
		}
	},
	N4(item, d) {
		return {
			text: say(__('The {0} lost its currency sign.'), titled('number card', d.chart)),
			todo: say(__('Add the sign to the card’s suffix.')),
			action: routeTo(item, __('Open chart')),
		}
	},
	N6(item, d) {
		return {
			text: say(__('The {0} now shows a total of all rows.'), titled('number card', d.chart)),
			todo: say(__('Pick a Date column to show a period.')),
			action: routeTo(item, __('Open chart')),
		}
	},
	N5(item, d) {
		return {
			text: say(
				__('The {0} now shows the total of the latest day of {1}.'),
				titled('number card', d.chart),
				em(d.column),
			),
			todo: say(__('Pick another period if it should show more than a day.')),
			action: routeTo(item, __('Open chart')),
		}
	},
	Q13(item, d, people, locale) {
		return {
			text: say(
				__('Fiscal years now start on {0}, from ERPNext’s current fiscal year.'),
				em(formatDay(d.start, locale)),
			),
			todo: say(__('Set Fiscal Year Start to choose.')),
			action:
				item.action === 'open_settings'
					? { kind: 'fix', label: __('Open settings') }
					: undefined,
		}
	},
	P11(item, d, people) {
		if (d.publisher_disabled) {
			return {
				text: say(
					__('The {0} was published by {1}, who is disabled, so guests see nothing.'),
					titled('chart', d.chart),
					em(person(people, d.publisher)),
				),
				todo: say(__('Turn on Run as owner in its sharing so guests see it again.')),
				action: routeTo(item, __('Open sharing'), { share: '1' }),
			}
		}
		// a move is told only when its new owner can't read its tables
		if (d.doctypes) {
			const access = giveReadAccess(item, people, d.publisher, d.doctypes)
			return {
				text: say(
					__(
						'The {0} now belongs to {1}, who published it, instead of {2}. {3} can’t read {4}, so its readers see Not Permitted.',
					),
					titled('chart', d.chart),
					em(person(people, d.publisher)),
					em(person(people, d.owner)),
					em(person(people, d.publisher, true)),
					tablesOf(d.doctypes),
				),
				todo: access.todo,
				action: access.action ?? routeTo(item, __('Open chart')),
			}
		}
	},
	P21(item, d) {
		if (d.cycle) {
			return {
				text: say(
					__('The {0} in the {1} reads the {2}, which reads it back.'),
					titled('query', d.query),
					titled('workbook', d.workbook),
					titled('query', d.source),
				),
				todo: say(__('Remove that source from one of them.')),
				action: routeTo(item, __('Open query')),
			}
		}
		return {
			text: say(
				__('The {0} was copied into the {1} without its secret {2}, so it won’t run.'),
				titled('script', d.query),
				titled('workbook', d.workbook),
				em(listOf(d.variables ?? [])),
			),
			todo: say(__('Enter {0} in the script again.'), em(listOf(d.variables ?? []))),
			action: routeTo(item, __('Open query')),
		}
	},
	W2(item, d) {
		const text = say(
			__('The {0} is a copy of an old Insights template. {1} replaces it and gets updates.'),
			titled('workbook', d.workbook),
			[
				{ text: d.app ? __('{0}’s', d.app) + ' ' : __('The') + ' ' },
				...titled('workbook', d.standard),
			],
		)
		if (item.action === 'delete_workbook') {
			return {
				text,
				todo: say(__('The copy was never changed, so delete it.')),
				action: { kind: 'fix', label: __('Delete copy') },
			}
		}
		return {
			text,
			todo: say(
				__('Move what you changed to the {0}, then delete the copy.'),
				titled('workbook', d.standard),
			),
			action: routeTo(item, __('Open workbook')),
		}
	},
	P20(item, d, people) {
		const kind =
			item.reference_doctype === 'Insights Chart v3'
				? 'chart'
				: item.reference_doctype === 'Insights Alert'
				  ? 'alert'
				  : 'script'
		return {
			text: say(
				__('Only admins can edit {0} {1} now. It still runs.'),
				em(possessive(people, d.author)),
				titled(kind, d.title),
			),
			todo: say(__('Ask an Insights Admin when it needs a change.')),
			action: routeTo(
				item,
				item.reference_doctype === 'Insights Chart v3'
					? __('Open chart')
					: item.reference_doctype === 'Insights Alert'
					  ? __('Open alert')
					  : __('Open query'),
			),
		}
	},
	Q1: refusedNames,
	J4: refusedNames,
	Q5: refusedNames,
	C4(item, d) {
		const lines: { statistic: string; removed: boolean; measure: string | null }[] =
			d.lines ?? []
		const parts = lines.map((line) =>
			line.removed
				? say(__('the {0} line is gone, as the chart plots only the count'), {
						text: line.statistic,
				  })
				: say(
						__('the {0} line reads {1} only'),
						{ text: line.statistic },
						em(line.measure ?? ''),
				  ),
		)
		return {
			text: say(
				__('On the {0}, {1}.'),
				titled('chart', d.chart),
				parts.flatMap((part, index) => (index ? [{ text: '; ' }, ...part] : part)),
			),
			todo: say(__('Check the chart still reads right.')),
			action: routeTo(item, __('Open chart')),
		}
	},
}

/** The doctypes a chart's tables need, or its tables when none names a doctype. */
function tablesOf(doctypes: string[] = []): Part {
	return doctypes.length ? em(listOf(doctypes.map(documents), 3)) : { text: __('its tables') }
}

/**
 * What lets a chart that runs as `user` run again: a desk role that reads its
 * doctypes, which the Access step asks for too.
 */
function giveReadAccess(
	item: UpgradeItem,
	people: People,
	user: string,
	doctypes: string[] = [],
): Pick<Sentence, 'todo' | 'action'> {
	// a table off the site database needs a team grant, which no role gives
	if (!doctypes.length) {
		return {
			todo: say(__('Give {0} its tables through an Insights team.'), {
				text: person(people, user),
			}),
			action: routeTo(item, __('Open chart')),
		}
	}
	const self = user === people.me
	return {
		todo: self
			? say(__('Give yourself a desk role that can read them.'))
			: say(__('Give {0} a desk role that can read them.'), { text: people.name(user) }),
		action: formAction(
			item,
			self ? __('Open your roles') : __('Open {0}’s roles', people.name(user)),
		),
	}
}

function memberKinds(kind: string) {
	return { chart: __('charts'), dashboard: __('dashboards'), query: __('queries') }[kind] ?? kind
}

function refusedNames(item: UpgradeItem, d: Record<string, any>): Sentence {
	return {
		text: say(
			__('The {0} uses {1}, which Insights v3.50 doesn’t allow, so it fails.'),
			titled(
				item.code === 'J4' ? 'import job' : item.code === 'Q5' ? d.kind : 'script',
				d.title,
			),
			em(listOf(d.names ?? [])),
		),
		todo: say(__('Remove {0} from it.'), em(listOf(d.names ?? []))),
		action: routeTo(item, __('Open it')) ?? formAction(item, __('Open it')),
	}
}
