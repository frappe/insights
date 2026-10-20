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

export type PictureName =
	| 'appDashboards'
	| 'showInDesk'
	| 'drill'
	| 'currency'
	| 'roles'
	| 'notPermitted'
	| 'shareBefore'
	| 'shareNow'
	| 'runAsOwner'
	| 'workbookAccess'
	| 'chartOwner'
	| 'numberCards'

/** What a slide's feature needs of the reader: the server says whether they have it. */
export type Can = { readStandardDashboards: boolean; showInDesk: boolean; share: boolean }

/** One feature a reader of Insights 3 meets first, and the screen it is on. */
export type Slide = { label: string; text: string; picture: PictureName; needs?: keyof Can }

// What a reader of Insights 3 gains most, one per slide. The last leads into
// the upgrade steps, which are mostly about permissions.
export const welcomeSlides = translatedTable<Slide[]>(() => [
	{
		label: __('Dashboards from ERPNext and Frappe HR'),
		text: __(
			'Selling, Stock, Accounts, Payroll and more come ready to use. Duplicate one to change it.',
		),
		picture: 'appDashboards',
		needs: 'readStandardDashboards',
	},
	{
		label: __('Charts on desk workspaces'),
		text: __('Pick Show in Desk on a chart to put it on a desk dashboard or workspace.'),
		picture: 'showInDesk',
		needs: 'showInDesk',
	},
	{
		label: __('Click a chart for its rows'),
		text: __('Click any bar to see the rows behind it, or break it down by another column.'),
		picture: 'drill',
	},
	{
		label: __('Your company, your currency'),
		text: __(
			'A Company filter opens on your default company, and amounts print in its currency.',
		),
		picture: 'currency',
	},
	{
		label: __('Share dashboards with desk roles'),
		text: __('Anyone with those roles can open the dashboard, even without an Insights role.'),
		picture: 'roles',
		needs: 'share',
	},
	{
		label: __('Desk permissions decide'),
		text: __('A chart shows only the rows desk lets you read, and names the access you lack.'),
		picture: 'notPermitted',
	},
])

/** The welcome slides of what the reader can do. */
export function slidesFor(can: Can): Slide[] {
	return welcomeSlides().filter((slide) => !slide.needs || can[slide.needs])
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

export type Step =
	| { id: 'welcome' | 'sharing'; label: string; section: 'new' }
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
		label: __('Public charts'),
		kind: 'now',
		codes: ['P10', 'P12'],
		title: __("Public charts show their owner's rows"),
		lead: [
			__('Public charts now run as their owner,'),
			__('so everyone who opens one sees the owner’s rows.'),
		],
		picture: 'runAsOwner',
	},
	{
		id: 'workbooks',
		label: __('Workbook access'),
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
			__('Insights 4 reads a few settings differently,'),
			__('so these show other numbers until you set them again.'),
		],
		picture: 'numberCards',
	},
	{
		id: 'notes',
		label: __('Good to know'),
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

// The Good to know step of someone who isn't an admin, when it holds more than
// moved charts: their own items an admin would find in Details for admins.
const yourNotes = translatedTable<Pick<Group, 'title' | 'lead'>>(() => ({
	title: __('A few changes to what you made'),
	lead: [__('The upgrade changed some of your work,'), __('and each change says what it means.')],
}))

// Items an ordinary admin does not act on in the wizard: nothing breaks if
// they wait, or they take a developer. Listed apart, in this order.
export const detailGroups = translatedTable<Record<string, string>>(() => ({
	P21: __('Scripts copied without their secrets'),
	Q1: __('Scripts that will fail'),
	J4: __('Import jobs that will fail'),
	Q5: __('Expressions that reach the database'),
	W2: __('Copies of Insights 3 templates'),
	P20: __('Code only admins can edit'),
	J1: __('Alerts that check a saved copy'),
	C4: __('Reference lines that moved'),
	N5: __('Number cards that show a day now'),
}))

// Detail items that tell of something failing until someone acts: a script or
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
 * The wizard's steps for this reader. A step with nothing in it is left out.
 *
 * A note only tells, so it stays for the person it is addressed to: an admin
 * gets no step for another user's note. Someone who isn't an admin finds their
 * own detail items in Good to know, as Details for admins is not theirs.
 */
export function wizardSteps(
	items: UpgradeItem[],
	options: { sharing: boolean; admin: boolean; me: string },
): Step[] {
	const steps: Step[] = [{ id: 'welcome', label: __('Welcome'), section: 'new' }]
	if (options.sharing) steps.push({ id: 'sharing', label: __('Sharing'), section: 'new' })
	const inSteps = new Set(groups().flatMap((group) => group.codes))
	for (const group of groups()) {
		const codes =
			group.kind === 'note' && !options.admin
				? [
						...group.codes,
						...items.map((item) => item.code).filter((code) => !inSteps.has(code)),
				  ]
				: group.codes
		const rows = rowsOf(
			items.filter(
				(item) =>
					codes.includes(item.code) &&
					(group.kind !== 'note' || !item.user || item.user === options.me),
			),
		)
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
				  { ...group, ...yourNotes(), codes, kind, picture: undefined }
				: { ...group, kind },
			rows,
		})
	}
	return steps
}

/**
 * Where the wizard opens for a stored step id. A step whose items were all
 * closed since is gone, and the reader goes on to the step after it.
 */
export function stepIndexOf(steps: Step[], id: string): number {
	const order = ['welcome', 'sharing', ...groups().map((group) => group.id)]
	const at = order.indexOf(id)
	const index = steps.findIndex((step) => order.indexOf(step.id) >= at)
	return index < 0 ? steps.length - 1 : index
}

/** The rows the wizard leaves to Details for admins, grouped and titled. */
export function detailsOf(
	items: UpgradeItem[],
	options: { admin: boolean },
): { title: string; rows: Row[] }[] {
	if (!options.admin) return []
	const inWizard = new Set(groups().flatMap((group) => group.codes))
	const titles = detailGroups()
	const order = Object.keys(titles)
	const byCode = new Map<string, Row[]>()
	for (const row of rowsOf(items)) {
		if (inWizard.has(row.item.code)) continue
		byCode.set(row.item.code, [...(byCode.get(row.item.code) ?? []), row])
	}
	const rank = (code: string) => (code in titles ? order.indexOf(code) : order.length)
	return [...byCode.entries()]
		.sort(([a], [b]) => rank(a) - rank(b))
		.map(([code, rows]) => ({ title: titles[code] ?? __('Other changes'), rows }))
}

/**
 * What a key does in the wizard. ← goes back on every step, → pages the welcome
 * slides, and Enter presses the screen's primary button unless focus is on
 * another control, which Enter presses itself. Typing in a field is left alone.
 */
export function keyAction(
	key: string,
	focus: { inField: boolean; onControl: boolean; moreSlides: boolean },
): 'back' | 'next' | 'primary' | undefined {
	if (focus.inField) return
	if (key === 'ArrowLeft') return 'back'
	if (key === 'ArrowRight' && focus.moreSlides) return 'next'
	if (key === 'Enter' && !focus.onControl) return 'primary'
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
const quoted = (title: string): Part => em(`“${title}”`)

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

function userForm(user: string, label: string): ItemAction {
	return { kind: 'form', label, url: `/desk/user/${encodeURIComponent(user)}` }
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
					? undefined
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
				action: {
					kind: 'form',
					label: __('Open User Permissions'),
					url: '/desk/user-permission',
				},
			}
		}
	},
	P10(item, d, people) {
		const rows =
			d.reason === 'script' || !d.table
				? em(__('{0} rows', possessive(people, d.owner)))
				: em(`${possessive(people, d.owner)} ${documents(d.table)}`)
		return {
			text: say(
				__('Everyone who opens {0} now sees {1}, not their own.'),
				quoted(d.chart),
				rows,
			),
			action: routeTo(item, __('Open sharing'), { share: '1' }),
		}
	},
	P12(item, d, people) {
		const owner = em(person(people, d.owner))
		const text =
			d.reason === 'disabled'
				? say(
						__('{0} can’t run as {1}, who is disabled, so guests see nothing.'),
						quoted(d.chart),
						owner,
				  )
				: d.reason === 'no_insights_role'
				  ? say(
							__(
								'{0} can’t run as {1}, who has no Insights role, so guests see nothing.',
							),
							quoted(d.chart),
							owner,
				    )
				  : say(
							__('{0} can’t run as {1} any more, so guests see nothing.'),
							quoted(d.chart),
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
				action: userForm(
					d.owner,
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
		const removed: { kind: string; title: string; write: boolean }[] = d.removed ?? []
		const users: string[] = d.users ?? []
		const text: Part[] = []
		if (users.length) {
			text.push(
				...say(
					__(
						'{0} can now open the whole workbook {1}, as some of its {2} were shared with them.',
					),
					em(names(people, users, true)),
					quoted(d.workbook),
					{ text: listOf((d.shared ?? []).map(memberKinds)) },
				),
			)
		}
		if (removed.length) {
			const shares = removed.map((share) =>
				say(
					share.write ? __('edit the {0} {1}') : __('open the {0} {1}'),
					{ text: memberKind(share.kind) },
					quoted(share.title),
				),
			)
			if (text.length) text.push({ text: ' ' })
			text.push(
				...say(
					removed.length > 1
						? __(
								'Everyone could {0}. Those shares are gone, so only people the workbook {1} is shared with can open them.',
						  )
						: __(
								'Everyone could {0}. That share is gone, so only people the workbook {1} is shared with can open it.',
						  ),
					joined(shares),
					quoted(d.workbook),
				),
			)
		}
		return { text, action: workbookSharing(item, __('Open workbook sharing')) }
	},
	P3(item, d, people) {
		const users: string[] = d.users ?? []
		const one = users.length === 1
		return {
			text: say(
				__('{0} made something in {1}, so {2} can now edit the whole workbook.'),
				em(names(people, users, true)),
				quoted(d.workbook),
				{ text: one ? person(people, users[0]) : __('they') },
			),
			action: workbookSharing(item, __('Open workbook sharing')),
		}
	},
	P4(item, d, people) {
		const users: string[] = d.users ?? []
		const teams: string[] = d.teams ?? []
		const titles = (d.items ?? []).map((title: string) => quoted(title))
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
			action: workbookSharing(
				item,
				users.length === 1
					? __('Share the workbook with {0}', person(people, users[0]))
					: __('Open workbook sharing'),
			),
		}
	},
	P19(item, d, people) {
		const alert = quoted(d.alert)
		let text: Part[]
		if (d.outcome === 'moved') {
			text = say(
				__('The alert {0} now runs as {1}, who owns its workbook, in place of {2}.'),
				alert,
				em(person(people, d.owner)),
				em(person(people, d.enabler)),
			)
		} else if (d.outcome === 'no_user') {
			text = say(__('The alert {0} has no one to run as, so it will stop.'), alert)
		} else {
			text = say(
				__('The alert {0} will stop, because {1} can’t edit its workbook.'),
				alert,
				em(person(people, d.enabler)),
			)
		}
		return {
			text,
			todo:
				d.outcome === 'moved' || !d.enabler
					? undefined
					: say(__('Share the workbook with {0} to edit.'), {
							text: person(people, d.enabler),
					  }),
			action: workbookSharing(item, __('Open workbook sharing')),
		}
	},
	K1(item, d) {
		return {
			text: say(
				__(
					'{0} lost its default date range ({1}), which Insights 3 showed but never applied.',
				),
				quoted(d.dashboard),
				{ text: `${d.start} – ${d.end}` },
			),
			todo: say(__('Set it again if you want it.')),
			action: routeTo(item, __('Open dashboard')),
		}
	},
	N4(item, d) {
		return {
			text: say(__('The number card {0} lost its currency sign.'), quoted(d.chart)),
			todo: say(__('Add the sign to the card’s suffix.')),
			action: routeTo(item, __('Open chart')),
		}
	},
	N6(item, d) {
		return {
			text: say(__('The number card {0} now shows a total of all rows.'), quoted(d.chart)),
			todo: say(__('Pick a Date column to show a period.')),
			action: routeTo(item, __('Open chart')),
		}
	},
	N5(item, d) {
		return {
			text: say(
				__('The number card {0} now shows the total of the latest day of {1}.'),
				quoted(d.chart),
				em(d.column),
			),
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
					__('{0} was published by {1}, who is disabled, so guests see nothing.'),
					quoted(d.chart),
					em(person(people, d.publisher)),
				),
				action: routeTo(item, __('Open chart')),
			}
		}
		return {
			text: say(
				__(
					'{0} now belongs to {1}, who published it, instead of {2}. Its readers see the same rows as before.',
				),
				quoted(d.chart),
				em(person(people, d.publisher)),
				em(person(people, d.owner)),
			),
			action: routeTo(item, __('Open chart')),
		}
	},
	P21(item, d) {
		if (d.cycle) {
			return {
				text: say(
					__('The query {0} in {1} reads {2}, which reads it back. Remove that source.'),
					quoted(d.query),
					quoted(d.workbook),
					quoted(d.source),
				),
				action: routeTo(item, __('Open query')),
			}
		}
		return {
			text: say(
				__(
					'The script {0} was copied into {1} without its secret {2}. It won’t run until someone enters it.',
				),
				quoted(d.query),
				quoted(d.workbook),
				em(listOf(d.variables ?? [])),
			),
			action: routeTo(item, __('Open query')),
		}
	},
	W2(item, d) {
		return {
			text: say(
				__('{0} is a copy of an Insights 3 template. {1} replaces it and gets updates.'),
				quoted(d.workbook),
				[{ text: d.app ? __('{0}’s', d.app) + ' ' : '' }, quoted(d.standard)],
			),
			action: routeTo(item, __('Open workbook')),
		}
	},
	P20(item, d, people) {
		const kind =
			item.reference_doctype === 'Insights Chart v3'
				? __('chart')
				: item.reference_doctype === 'Insights Alert'
				  ? __('alert')
				  : __('script')
		return {
			text: say(
				__('Only admins can edit {0} {1} {2} now. It still runs.'),
				em(possessive(people, d.author)),
				{ text: kind },
				quoted(d.title),
			),
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
	J1(item, d) {
		return {
			text: say(
				__(
					'The alert {0} checks a saved copy of {1}. Changes to the chart don’t reach it.',
				),
				quoted(d.alert),
				quoted(d.chart),
			),
			action: routeTo(item, __('Open query')),
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
				__('On {0}, {1}. Check it still looks right.'),
				quoted(d.chart),
				parts.flatMap((part, index) => (index ? [{ text: '; ' }, ...part] : part)),
			),
			action: routeTo(item, __('Open chart')),
		}
	},
}

function memberKind(kind: string) {
	return { chart: __('chart'), dashboard: __('dashboard'), query: __('query') }[kind] ?? kind
}

function memberKinds(kind: string) {
	return { chart: __('charts'), dashboard: __('dashboards'), query: __('queries') }[kind] ?? kind
}

function refusedNames(item: UpgradeItem, d: Record<string, any>): Sentence {
	return {
		text: say(
			__(
				'{0} uses {1}, which Insights 4 doesn’t allow. It will fail until they are removed.',
			),
			quoted(d.title),
			em(listOf(d.names ?? [])),
		),
		action: routeTo(item, __('Open it')) ?? formAction(item, __('Open it')),
	}
}
