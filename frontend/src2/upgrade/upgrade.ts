import { useStorage } from '@vueuse/core'
import { call } from 'frappe-ui'
import { computed, reactive, ref, watch } from 'vue'
import { showErrorToast } from '../helpers'
import session from '../session'
import { stepIndexOf, wizardSteps, type Can } from './upgrade_steps'

export type UpgradeItem = {
	name: string
	code: string
	/** Done when its fix was applied, Dismissed when the reader marked it done. */
	status: 'Open' | 'Done' | 'Dismissed'
	message: string
	reference_doctype: string | null
	reference_name: string | null
	user: string | null
	action: '' | 'delete_workbook' | 'open_settings' | null
	/** The names and values the item's sentence shows, by key, as the patch stored them. */
	data?: Record<string, any>
	/** Each user the data names, as the sentence calls them. */
	people?: Record<string, { full_name: string; first_name: string }>
	/** The workbook the reference is opened in, if it has a route in the app. */
	workbook: string | null
	/** The desk form of a reference the app has no page for, such as a user. */
	form_url: string | null
	/** Whether the user holds the permission the fix needs. */
	can_fix: boolean
}

/** Where the reader left the wizard, kept in the browser so Resume returns there. */
type Progress = {
	step: string
	/** Steps the reader has looked at. */
	seen: string[]
	/** Whether the wizard was ever opened here. Until then there is nothing to resume. */
	started: boolean
	finished: boolean
}

const freshProgress = (): Progress => ({
	step: 'welcome',
	seen: [],
	started: false,
	finished: false,
})

const items = ref<UpgradeItem[]>([])
const loaded = ref(false)
const showWizard = ref(false)

let stored: ReturnType<typeof useStorage<Progress>> | undefined
function progressStore() {
	stored ??= useStorage<Progress>(
		`insights:upgrade-wizard:${session.user.email}`,
		freshProgress(),
		localStorage,
		{ mergeDefaults: true },
	)
	return stored
}

// the server's rule for who works through every item, so the steps match the items it sent
const admin = computed(() => Boolean(session.user.is_upgrade_admin))
const can = computed<Can>(() => ({
	readStandardDashboards: Boolean(session.user.reads_standard_dashboards),
	// as the chart's own menu offers it
	showInDesk: Boolean(session.user.has_desk_access && session.user.can_show_in_desk),
	share: admin.value || Boolean(session.user.owns_workbooks),
}))

const steps = computed(() =>
	wizardSteps(items.value, {
		can: can.value,
		admin: admin.value,
		me: session.user.email,
	}),
)

const doneNames = computed(
	() => new Set(items.value.filter((item) => item.status !== 'Open').map((item) => item.name)),
)
const isDone = (name: string) => doneNames.value.has(name)

function setStatus(names: string[], status: UpgradeItem['status']) {
	for (const item of items.value) if (names.includes(item.name)) item.status = status
}

const openCount = computed(() => items.value.filter((item) => !isDone(item.name)).length)
watch(openCount, (count) => (session.user.upgrade_item_count = count))

const stepIndex = computed(() => stepIndexOf(steps.value, progressStore().value.step))

const openWizardItems = computed(() =>
	steps.value
		.flatMap((step) => ('rows' in step ? step.rows : []))
		.filter((row) => !isDone(row.item.name)),
)

async function load() {
	try {
		items.value = await call('insights.api.upgrade.get_upgrade_items')
		loaded.value = true
	} catch (error) {
		showErrorToast(error as Error, false)
	}
}

// Marks a page the wizard opened in a new tab, so the wizard does not open over it there.
const FROM_WIZARD = 'from_upgrade'

export function linkFromWizard<T extends { query?: Record<string, any> }>(route: T): T {
	return { ...route, query: { ...route.query, [FROM_WIZARD]: '1' } }
}

/** Whether the wizard opens by itself on this page: until Finish or Skip, except over a page it opened. */
function opensByItself() {
	return (
		Boolean(session.user.upgrade_unseen) &&
		!new URLSearchParams(window.location.search).has(FROM_WIZARD)
	)
}

function open() {
	showWizard.value = true
	progressStore().value.started = true
	return loaded.value ? Promise.resolve() : load()
}

/** Puts the wizard away for this visit. The sidebar card resumes it, and the next visit opens it again. */
function close() {
	showWizard.value = false
}

function goTo(id: string) {
	const progress = progressStore().value
	if (progress.step !== id) progress.seen = [...new Set([...progress.seen, progress.step])]
	progress.step = id
}

/** Ends the wizard on Finish or Skip. It no longer opens by itself. */
async function finish() {
	const progress = progressStore().value
	progress.seen = [...new Set([...progress.seen, progress.step])]
	progress.finished = true
	close()
	if (!session.user.upgrade_unseen) return
	session.user.upgrade_unseen = false
	await call('insights.api.upgrade.mark_upgrade_seen').catch((error: Error) =>
		showErrorToast(error, false),
	)
}

/** Back at the first step with items left. */
function resume() {
	const progress = progressStore().value
	if (progress.finished) {
		const next = steps.value.find(
			(step) => 'rows' in step && step.rows.some((row) => !isDone(row.item.name)),
		)
		progress.step = next?.id ?? 'welcome'
		progress.finished = false
	}
	return open()
}

/**
 * Marks every item of a row done: an admin closes both sides of a change at once.
 * One closed elsewhere since the wizard loaded is done all the same.
 */
async function markDone(names: string[]) {
	try {
		await call('insights.api.upgrade.dismiss_upgrade_items', { names })
	} catch (error) {
		showErrorToast(error as Error, false)
		return
	}
	setStatus(names, 'Dismissed')
}

/** Opens a row's items again. */
async function reopen(names: string[]) {
	try {
		await call('insights.api.upgrade.reopen_upgrade_items', { names })
	} catch (error) {
		showErrorToast(error as Error, false)
		return
	}
	setStatus(names, 'Open')
}

async function fix(item: UpgradeItem) {
	try {
		await call('insights.api.upgrade.fix_upgrade_item', { name: item.name })
	} catch (error) {
		showErrorToast(error as Error, false)
		return
	}
	setStatus([item.name], 'Done')
}

const upgrade = reactive({
	items,
	loaded,
	showWizard,
	steps,
	stepIndex,
	openWizardItems,
	progress: computed(() => progressStore().value),
	isDone,
	load,
	opensByItself,
	open,
	close,
	goTo,
	finish,
	resume,
	markDone,
	reopen,
	fix,
})

export default upgrade
