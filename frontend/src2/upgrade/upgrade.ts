import { useStorage } from '@vueuse/core'
import { call } from 'frappe-ui'
import { computed, reactive, ref, watch } from 'vue'
import { showErrorToast } from '../helpers'
import session from '../session'
import { slidesFor, stepIndexOf, wizardSteps } from './upgrade_steps'

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
	slide: number
	/** Steps the reader has looked at. */
	seen: string[]
	/** Items put off for later. They stay open on the server. */
	skipped: string[]
	/** Whether the wizard was ever opened here. Until then there is nothing to resume. */
	started: boolean
	finished: boolean
}

const freshProgress = (): Progress => ({
	step: 'welcome',
	slide: 0,
	seen: [],
	skipped: [],
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
const sharing = computed(() => admin.value || Boolean(session.user.owns_workbooks))

const slides = computed(() =>
	slidesFor({
		readStandardDashboards: Boolean(session.user.reads_standard_dashboards),
		// as the chart's own menu offers it
		showInDesk: Boolean(session.user.has_desk_access && session.user.can_show_in_desk),
		share: sharing.value,
	}),
)

const steps = computed(() =>
	wizardSteps(items.value, {
		sharing: sharing.value,
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

function open() {
	showWizard.value = true
	progressStore().value.started = true
	return loaded.value ? Promise.resolve() : load()
}

/** Closes the wizard. It no longer opens by itself, and the sidebar card resumes it. */
async function close() {
	showWizard.value = false
	// one step has nowhere to resume to
	if (steps.value.length === 1) progressStore().value.finished = true
	if (!session.user.upgraded_from_v3) return
	session.user.upgraded_from_v3 = false
	await call('insights.api.upgrade.mark_upgrade_seen').catch((error: Error) =>
		showErrorToast(error, false),
	)
}

function goTo(id: string, slide?: number) {
	const progress = progressStore().value
	if (progress.step !== id) progress.seen = [...new Set([...progress.seen, progress.step])]
	progress.step = id
	if (slide !== undefined) progress.slide = slide
}

function finish() {
	const progress = progressStore().value
	progress.seen = [...new Set([...progress.seen, progress.step])]
	progress.finished = true
	return close()
}

/** Back at the first step with items left, with the skipped ones in line again. */
function resume() {
	const progress = progressStore().value
	if (progress.finished) {
		const next = steps.value.find(
			(step) => 'rows' in step && step.rows.some((row) => !isDone(row.item.name)),
		)
		progress.step = next?.id ?? 'welcome'
		progress.skipped = []
		progress.finished = false
	}
	return open()
}

function skip(name: string) {
	const progress = progressStore().value
	progress.skipped = [...new Set([...progress.skipped, name])]
}

function unskip(names: string[]) {
	const progress = progressStore().value
	progress.skipped = progress.skipped.filter((name) => !names.includes(name))
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

/** Puts a row's items back in the queue. */
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
	slides,
	steps,
	stepIndex,
	openWizardItems,
	progress: computed(() => progressStore().value),
	isDone,
	load,
	open,
	close,
	goTo,
	finish,
	resume,
	skip,
	unskip,
	markDone,
	reopen,
	fix,
})

export default upgrade
