<script setup lang="ts">
import { KeyboardShortcut, Popover } from 'frappe-ui'
import {
	ArrowLeft,
	ArrowRight,
	Check,
	ChevronLeft,
	ChevronRight,
	ExternalLink,
	Info,
	Undo2,
	X,
} from 'lucide-vue-next'
import { computed, defineAsyncComponent, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { confirmDialog } from '../helpers/confirm_dialog'
import session from '../session'
import { __ } from '../translation'
import UpgradePicture from './pictures/UpgradePicture.vue'
import upgrade, { linkFromWizard } from './upgrade'
import UpgradeSentence from './UpgradeSentence.vue'
import {
	keyAction,
	nextOpenIndex,
	pictureOf,
	sentenceOf,
	startIndex,
	stepBadge,
	type ItemAction,
	type Row,
	type Sentence,
	type Step,
} from './upgrade_steps'

const Settings = defineAsyncComponent(() => import('../settings/Settings.vue'))

const RELEASE_NOTES = 'https://github.com/frappe/insights/releases'

const props = defineProps<{ step: Step }>()
const emit = defineEmits<{ close: [] }>()

const router = useRouter()
const index = computed(() => upgrade.steps.findIndex((step) => step.id === props.step.id))
const isLast = computed(() => index.value === upgrade.steps.length - 1)
const feature = computed(() => ('feature' in props.step ? props.step.feature : undefined))
const hasUpgradeSteps = computed(() => upgrade.steps.some((step) => step.section === 'upgrade'))

const rows = computed(() => ('rows' in props.step ? props.step.rows : []))
const group = computed(() => ('group' in props.step ? props.step.group : undefined))
const isDone = (row: Row) => row.names.every((name) => upgrade.isDone(name))
const openCount = computed(() => rows.value.filter((row) => !isDone(row)).length)
const doneCount = computed(() => rows.value.length - openCount.value)

// The item the reader moved to. Unset, the step shows where it starts.
const cursor = ref<string>()
watch(
	() => props.step.id,
	() => (cursor.value = undefined),
)
const itemIndex = computed(() => {
	const at = rows.value.findIndex((row) => row.item.name === cursor.value)
	return at === -1 ? startIndex(rows.value, isDone) : at
})
const current = computed<Row | undefined>(() => rows.value[itemIndex.value])
const currentDone = computed(() => Boolean(current.value && isDone(current.value)))
const picture = computed(
	() => group.value?.picture ?? (current.value ? pictureOf(current.value.item) : undefined),
)
const badge = computed(() => stepBadge(openCount.value, group.value?.kind ?? 'note'))
const sentenceFor = (row: Row) => sentenceOf(row.item, session.user.email, session.user.locale)
const sentence = computed(() => (current.value ? sentenceFor(current.value) : undefined))

/** The row's button, unless it is a fix the reader may not apply, or one already applied. */
function actionOf(row: Row, of: Sentence): ItemAction | undefined {
	if (!of.action) return
	if (of.action.kind !== 'fix' || (row.item.can_fix && row.item.status !== 'Done')) {
		return of.action
	}
}

const currentAction = computed(() =>
	current.value && sentence.value ? actionOf(current.value, sentence.value) : undefined,
)

// Who the share rows in a picture show: the person the current item is about,
// else the one the reader's items name most, else the reader.
const PERSON_KEYS = ['publisher', 'user', 'users', 'enabler', 'owner', 'author', 'members']
const person = computed(() => {
	const allRows = upgrade.steps.flatMap((s) => ('rows' in s ? s.rows : []))
	const named = (row: Row) =>
		PERSON_KEYS.flatMap((key) => [row.item.data?.[key]].flat()).filter(
			(user): user is string =>
				typeof user === 'string' &&
				user !== session.user.email &&
				Boolean(row.item.people?.[user]),
		)
	let email = current.value ? named(current.value)[0] : undefined
	if (!email) {
		const counts = new Map<string, number>()
		for (const user of allRows.flatMap(named)) counts.set(user, (counts.get(user) ?? 0) + 1)
		email = [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0]
	}
	const people = Object.assign({}, ...allRows.map((row) => row.item.people ?? {}))
	if (email) return { email, full_name: people[email]?.full_name ?? email }
	const full_name = [session.user.first_name, session.user.last_name].filter(Boolean).join(' ')
	return { email: session.user.email, full_name: full_name || session.user.email }
})

function goToIndex(next: number) {
	const step = upgrade.steps[next]
	if (step) upgrade.goTo(step.id)
}

function next() {
	if (isLast.value) {
		upgrade.finish()
		return
	}
	goToIndex(index.value + 1)
}

function back() {
	if (index.value > 0) goToIndex(index.value - 1)
}

const showSettings = ref(false)
const pending = ref(false)

function openAction(action: ItemAction, row: Row) {
	if (action.kind === 'fix') {
		applyFix(row)
		return
	}
	// a new tab, so the wizard stays where the reader is
	const url =
		action.kind === 'form' ? action.url : router.resolve(linkFromWizard(action.route)).href
	window.open(url, '_blank', 'noopener')
}

function applyFix(row: Row) {
	const { item } = row
	if (item.action === 'open_settings') {
		showSettings.value = true
		return
	}
	confirmDialog({
		title: __('Delete {0}?', `“${item.data?.workbook}”`),
		message: __(
			'The copy was never changed, and {0} replaces it. This cannot be undone.',
			`“${item.data?.standard}”`,
		),
		theme: 'red',
		primaryActionLabel: __('Delete copy'),
		onSuccess: () => upgrade.fix(item),
	})
}

function moveTo(at: number) {
	const row = rows.value[at]
	if (row) cursor.value = row.item.name
}

async function markDone(row: Row) {
	// held here, as the step's start moves once the row is done
	cursor.value = row.item.name
	pending.value = true
	await upgrade.markDone(row.names)
	pending.value = false
	if (isDone(row)) moveTo(nextOpenIndex(rows.value, itemIndex.value, isDone))
}

function undo(row: Row) {
	cursor.value = row.item.name
	upgrade.reopen(row.names)
}

// The primary button takes focus on every screen, so Enter presses it.
const body = ref<HTMLElement>()
function focusPrimary() {
	nextTick(() => {
		const root = body.value?.closest('[data-upgrade-step]')
		;(root?.querySelector('[data-primary]') as HTMLElement | null)?.focus({
			preventScroll: true,
		})
	})
}
onMounted(focusPrimary)
watch(() => [props.step.id, current.value?.item.name, currentDone.value], focusPrimary)

function onKeydown(event: KeyboardEvent) {
	const target = event.target as HTMLElement
	const action = keyAction(event.key, {
		inField: Boolean(target.closest('input, textarea, [contenteditable="true"]')),
		onControl: Boolean(target.closest('button, a')),
		hasNext: Boolean(group.value) && itemIndex.value < rows.value.length - 1,
	})
	const primary = body.value
		?.closest('[data-upgrade-step]')
		?.querySelector<HTMLElement>('[data-primary]')
	if (!action || (action === 'primary' && !primary)) return
	event.preventDefault()
	if (action === 'back' && group.value && itemIndex.value > 0) moveTo(itemIndex.value - 1)
	else if (action === 'back') back()
	else if (action === 'next' && group.value) moveTo(itemIndex.value + 1)
	else if (action === 'next') next()
	else primary!.click()
}
</script>

<template>
	<div
		data-upgrade-step
		class="relative flex min-h-0 flex-1 flex-col text-start"
		@keydown="onKeydown"
	>
		<Button
			variant="ghost"
			class="!absolute right-3 top-3 z-10"
			:aria-label="__('Close, and resume later from the sidebar')"
			:tooltip="__('Close (Esc)')"
			@click="emit('close')"
		>
			<template #icon><X class="size-4 text-ink-gray-9" stroke-width="1.5" /></template>
		</Button>

		<div ref="body" class="flex min-h-0 flex-1 flex-col gap-3.5 overflow-y-auto px-8 pb-5 pt-6">
			<template v-if="props.step.id === 'welcome'">
				<div class="flex grow flex-col items-center justify-center gap-3 text-center">
					<img src="../assets/insights-logo-new.svg" alt="" class="size-12 rounded-7" />
					<h2 class="mt-2 text-3xl font-semibold text-ink-gray-9">
						{{ __('Welcome to Insights v3.50') }}
					</h2>
					<p class="max-w-[460px] text-p-base text-ink-gray-6">
						{{
							hasUpgradeSteps
								? __(
										'This site now runs Insights v3.50. The next pages show what is new, then what the upgrade left for you.',
								  )
								: __(
										'This site now runs Insights v3.50. The next pages show what is new.',
								  )
						}}
					</p>
				</div>
			</template>

			<!-- Sharing: before on top, now below -->
			<template v-else-if="props.step.id === 'sharing' && feature">
				<h2 class="text-3xl font-semibold text-ink-gray-9">{{ feature.title }}</h2>
				<div class="flex grow flex-col gap-2.5">
					<div><Badge size="md" :label="__('Before')" /></div>
					<p class="text-p-base text-ink-gray-5">
						<span class="font-semibold text-ink-gray-9">
							{{ __('You shared each chart or dashboard on its own,') }}
						</span>
						{{ __('and could let people edit it.') }}
					</p>
					<div
						class="flex grow items-center justify-center rounded-5 bg-surface-alpha-gray-1 p-3.5 pb-2.5"
					>
						<UpgradePicture name="shareBefore" :person="person" />
					</div>
				</div>
				<div class="mt-1 flex grow flex-col gap-2.5">
					<div><Badge size="md" theme="blue" :label="__('Now')" /></div>
					<p class="text-p-base text-ink-gray-5">
						<span class="font-semibold text-ink-gray-9">{{ feature.lead[0] }}</span>
						{{ feature.lead[1] }}
					</p>
					<div
						class="flex grow items-center justify-center rounded-5 bg-surface-alpha-gray-1 p-3.5 pb-2.5"
					>
						<UpgradePicture name="shareNow" :person="person" />
					</div>
				</div>
			</template>

			<!-- A feature: what the reader gets, then the screen it is on -->
			<template v-else-if="feature">
				<div class="flex items-center gap-1.5">
					<h2 class="text-3xl font-semibold text-ink-gray-9">{{ feature.title }}</h2>
					<Popover v-if="feature.info" side="bottom" align="start">
						<template #trigger>
							<Button variant="ghost" :aria-label="__('About this release')">
								<template #icon>
									<Info class="size-4 text-ink-gray-5" stroke-width="1.5" />
								</template>
							</Button>
						</template>
						<div class="flex w-72 flex-col gap-2 p-3 text-p-sm text-ink-gray-7">
							<p>{{ feature.info }}</p>
							<a
								:href="RELEASE_NOTES"
								target="_blank"
								rel="noopener"
								class="self-start rounded-2 text-ink-gray-8 underline hover:text-ink-gray-9 focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
								>{{ __('Release notes') }}</a
							>
						</div>
					</Popover>
				</div>
				<p class="-mt-1.5 max-w-[620px] text-p-base text-ink-gray-5">
					<span class="font-semibold text-ink-gray-9">{{ feature.lead[0] }}</span>
					{{ feature.lead[1] }}
				</p>
				<div
					v-if="feature.picture"
					class="flex grow items-center justify-center rounded-5 bg-surface-alpha-gray-1 p-5"
				>
					<UpgradePicture :name="feature.picture" :person="person" />
				</div>
			</template>

			<!-- A group: what changed, the picture, then one item at a time -->
			<template v-else-if="group">
				<div>
					<Badge size="md" :theme="badge.theme" :label="badge.label" />
				</div>
				<h2 class="-mt-1.5 text-3xl font-semibold text-ink-gray-9">{{ group.title }}</h2>
				<p class="-mt-1.5 max-w-[620px] text-p-base text-ink-gray-5">
					<span class="font-semibold text-ink-gray-9">{{ group.lead[0] }}</span>
					{{ group.lead[1] }}
				</p>
				<!-- The picture grows into the room the dialog leaves, and the item below
				     keeps one height through the step, so nothing moves from item to item
				     and no band is left empty. An item without a picture takes its place. -->
				<div
					v-if="picture"
					class="flex shrink-0 grow basis-[220px] items-center justify-center rounded-5 bg-surface-alpha-gray-1 p-2.5"
				>
					<UpgradePicture
						:name="picture"
						:person="person"
						:doctype="current?.item.data?.doctypes?.[0]"
					/>
				</div>

				<div
					v-if="current && sentence"
					class="flex min-h-[196px] shrink-0 flex-col gap-3 rounded-5 border border-outline-gray-2 bg-surface-base px-4 py-3.5 shadow-sm"
					aria-live="polite"
				>
					<div class="flex items-center gap-2.5 text-xs text-ink-gray-5 tabular-nums">
						<span>{{
							__('{0} of {1}', String(itemIndex + 1), String(rows.length))
						}}</span>
						<div
							class="h-1 max-w-[120px] flex-1 overflow-hidden rounded-1 bg-surface-gray-2"
						>
							<div
								class="h-full rounded-1 bg-surface-gray-10"
								:style="{
									width: `${Math.round((doneCount / rows.length) * 100)}%`,
								}"
							/>
						</div>
						<span class="flex-1" />
						<div v-if="rows.length > 1" class="-my-1 -mr-1.5 flex">
							<Button
								variant="ghost"
								size="sm"
								:aria-label="__('Previous')"
								:tooltip="__('Previous (←)')"
								:disabled="itemIndex === 0"
								@click="moveTo(itemIndex - 1)"
							>
								<template #icon>
									<ChevronLeft class="size-4" stroke-width="1.5" />
								</template>
							</Button>
							<Button
								variant="ghost"
								size="sm"
								:aria-label="__('Next')"
								:tooltip="__('Next (→)')"
								:disabled="itemIndex === rows.length - 1"
								@click="moveTo(itemIndex + 1)"
							>
								<template #icon>
									<ChevronRight class="size-4" stroke-width="1.5" />
								</template>
							</Button>
						</div>
					</div>
					<p
						class="text-p-md"
						:class="currentDone ? 'text-ink-gray-5' : 'text-ink-gray-6'"
					>
						<UpgradeSentence :parts="sentence.text" :muted="currentDone" />
					</p>
					<div
						v-if="sentence.todo"
						class="-mt-1 flex items-center gap-2 text-p-base font-medium"
						:class="currentDone ? 'text-ink-gray-5' : 'text-ink-gray-8'"
					>
						<span
							class="grid size-5 shrink-0 place-items-center rounded-full bg-surface-gray-2"
						>
							<ArrowRight class="size-3" stroke-width="2" />
						</span>
						<span><UpgradeSentence :parts="sentence.todo" :muted="currentDone" /></span>
					</div>
					<div class="mt-auto flex items-center gap-2">
						<Button
							v-if="currentAction"
							variant="subtle"
							@click="openAction(currentAction, current)"
						>
							{{ currentAction.label }}
							<template v-if="currentAction.kind === 'form'" #suffix>
								<ExternalLink class="size-3.5 text-ink-gray-7" stroke-width="1.5" />
							</template>
						</Button>
						<span class="flex-1" />
						<template v-if="currentDone">
							<span class="flex items-center gap-1 text-sm text-ink-gray-5">
								<Check class="size-3.5 text-ink-green-7" stroke-width="2" />
								{{ __('Done') }}
							</span>
							<!-- a fix that was applied, as a deleted copy, can't be put back -->
							<Button
								v-if="current.item.status !== 'Done'"
								variant="ghost"
								:aria-label="__('Undo')"
								:tooltip="__('Put it back in the list')"
								@click="undo(current)"
							>
								<template #icon>
									<Undo2 class="size-4 text-ink-gray-6" stroke-width="1.5" />
								</template>
							</Button>
						</template>
						<Button
							v-else
							data-primary
							variant="solid"
							:loading="pending"
							@click="markDone(current)"
						>
							{{ group.kind === 'note' ? __('Got it') : __('Done') }}
							<template #suffix>
								<KeyboardShortcut
									combo="Enter"
									use-icons
									class="!text-ink-gray-4"
								/>
							</template>
						</Button>
					</div>
				</div>
			</template>
		</div>

		<div class="flex items-center gap-2 border-t border-outline-gray-1 py-3 pl-6 pr-5">
			<Button v-if="index > 0" variant="ghost" :label="__('Back')" @click="back">
				<template #prefix><ArrowLeft class="size-4" stroke-width="1.5" /></template>
			</Button>
			<span class="flex-1" />
			<Button v-if="!isLast" variant="ghost" :label="__('Skip')" @click="upgrade.finish()" />
			<Button
				v-if="group && openCount"
				variant="subtle"
				:label="__('Later')"
				:tooltip="__('The rest stay in your list')"
				@click="next"
			/>
			<Button v-else data-primary variant="solid" @click="next">
				{{
					group
						? isLast
							? __('Finish')
							: __('Next')
						: isLast
						  ? __('Done')
						  : __('Continue')
				}}
				<template #suffix>
					<KeyboardShortcut combo="Enter" use-icons class="!text-ink-gray-4" />
				</template>
			</Button>
		</div>
	</div>

	<Settings v-if="showSettings" v-model="showSettings" :tab="__('General')" />
</template>
