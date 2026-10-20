<script setup lang="ts">
import { KeyboardShortcut } from 'frappe-ui'
import { ArrowLeft, ArrowRight, Check, ExternalLink, Info, X } from 'lucide-vue-next'
import { computed, defineAsyncComponent, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import session from '../session'
import { __ } from '../translation'
import UpgradePicture from './pictures/UpgradePicture.vue'
import upgrade from './upgrade'
import UpgradeSentence from './UpgradeSentence.vue'
import {
	keyAction,
	pictureOf,
	sentenceOf,
	type ItemAction,
	type Row,
	type Step,
} from './upgrade_steps'

const Settings = defineAsyncComponent(() => import('../settings/Settings.vue'))

const RELEASE_NOTES = 'https://github.com/frappe/insights/releases'

const props = defineProps<{ step: Step }>()
const emit = defineEmits<{ close: [] }>()

const router = useRouter()
const slides = computed(() => upgrade.slides)
const progress = computed(() => upgrade.progress)
const index = computed(() => upgrade.steps.findIndex((step) => step.id === props.step.id))
const isLast = computed(() => index.value === upgrade.steps.length - 1)
const slide = computed(() => Math.min(progress.value.slide, slides.value.length - 1))
const onLastSlide = computed(() => slide.value === slides.value.length - 1)
const firstScreen = computed(() => index.value === 0 && slide.value === 0)

const rows = computed(() => ('rows' in props.step ? props.step.rows : []))
const group = computed(() => ('group' in props.step ? props.step.group : undefined))
const skipped = computed(() => new Set(progress.value.skipped))
const isDone = (row: Row) => row.names.every((name) => upgrade.isDone(name))
const queue = computed(() =>
	rows.value.filter((row) => !isDone(row) && !skipped.value.has(row.item.name)),
)
const doneCount = computed(() => rows.value.filter(isDone).length)
const skippedCount = computed(
	() => rows.value.filter((row) => !isDone(row) && skipped.value.has(row.item.name)).length,
)
const current = computed(() => queue.value[0])
const handled = computed(() => rows.value.length - queue.value.length)
const picture = computed(
	() => group.value?.picture ?? (current.value ? pictureOf(current.value.item) : undefined),
)
const badge = computed<{ theme: 'green' | 'amber' | 'gray'; label: string }>(() => {
	if (!current.value && !skippedCount.value) return { theme: 'green', label: __('Done') }
	return group.value?.kind === 'now'
		? { theme: 'amber', label: __('Needs you now') }
		: { theme: 'gray', label: __('Nothing to do') }
})
const sentence = computed(() =>
	current.value
		? sentenceOf(current.value.item, session.user.email, session.user.locale)
		: undefined,
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
	if (props.step.id === 'welcome' && !onLastSlide.value) {
		upgrade.goTo('welcome', slide.value + 1)
		return
	}
	if (isLast.value) {
		upgrade.finish()
		return
	}
	goToIndex(index.value + 1)
}

function back() {
	if (props.step.id === 'welcome' && slide.value > 0) {
		upgrade.goTo('welcome', slide.value - 1)
		return
	}
	if (index.value > 0) goToIndex(index.value - 1)
}

const showSettings = ref(false)
const pending = ref(false)

function openAction(action: ItemAction) {
	if (action.kind === 'fix') {
		showSettings.value = true
		return
	}
	// a new tab, so the wizard stays where the reader is
	const url = action.kind === 'form' ? action.url : router.resolve(action.route).href
	window.open(url, '_blank', 'noopener')
}

async function markDone(row: Row) {
	pending.value = true
	await upgrade.markDone(row.names)
	pending.value = false
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
watch(
	() => [props.step.id, slide.value, current.value?.item.name, queue.value.length],
	focusPrimary,
)

function onKeydown(event: KeyboardEvent) {
	const target = event.target as HTMLElement
	const action = keyAction(event.key, {
		inField: Boolean(target.closest('input, textarea, [contenteditable="true"]')),
		onControl: Boolean(target.closest('button, a')),
		moreSlides: props.step.id === 'welcome' && !onLastSlide.value,
	})
	const primary = body.value
		?.closest('[data-upgrade-step]')
		?.querySelector<HTMLElement>('[data-primary]')
	if (!action || (action === 'primary' && !primary)) return
	event.preventDefault()
	if (action === 'back') back()
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
			<!-- Welcome: one feature per slide -->
			<template v-if="props.step.id === 'welcome'">
				<h2 class="text-3xl font-semibold text-ink-gray-9">
					{{ __('Welcome to Insights 4') }}
				</h2>
				<div class="flex flex-col items-center gap-2.5 text-center">
					<div
						class="flex h-[300px] w-full items-center justify-center rounded-5 bg-surface-alpha-gray-1 p-5"
					>
						<UpgradePicture :name="slides[slide].picture" :person="person" />
					</div>
					<div class="mt-1.5 text-2xl font-semibold text-ink-gray-9">
						{{ slides[slide].label }}
					</div>
					<p class="max-w-[460px] text-p-base text-ink-gray-6">
						{{ slides[slide].text }}
					</p>
					<div class="mt-1 flex gap-1.5" role="tablist">
						<Button
							v-for="(item, i) in slides"
							:key="item.label"
							variant="ghost"
							class="!h-[7px] !min-h-0 !p-0"
							:class="
								i === slide
									? '!w-[18px] !rounded-[4px] !bg-surface-gray-9'
									: '!w-[7px] !rounded-full !bg-surface-gray-4'
							"
							role="tab"
							:aria-selected="i === slide"
							:aria-label="item.label"
							@click="upgrade.goTo('welcome', i)"
						/>
					</div>
				</div>
				<!-- kept in place on every slide, so the reader's dialog doesn't grow on the last -->
				<div
					class="mt-1 flex items-center gap-2 text-p-sm text-ink-gray-6"
					:class="onLastSlide ? '' : 'invisible'"
					:aria-hidden="!onLastSlide"
				>
					<Info class="size-4 shrink-0 text-ink-gray-5" stroke-width="1.5" />
					<span>
						{{ __('A few numbers change because Insights 3 computed them wrongly.') }}
						<a
							:href="RELEASE_NOTES"
							target="_blank"
							rel="noopener"
							class="text-ink-blue-link hover:underline"
							>{{ __('Release notes') }}</a
						>
					</span>
				</div>
			</template>

			<!-- Sharing: before on top, now below -->
			<template v-else-if="props.step.id === 'sharing'">
				<h2 class="text-3xl font-semibold text-ink-gray-9">
					{{ __('Share the workbook, not the chart') }}
				</h2>
				<div class="flex flex-col gap-2.5">
					<div class="text-xs font-semibold text-ink-gray-5">{{ __('Before') }}</div>
					<p class="text-p-base text-ink-gray-5">
						<span class="font-semibold text-ink-gray-9">
							{{
								__('In Insights 3, you shared each chart or dashboard on its own,')
							}}
						</span>
						{{ __('and could let people edit it.') }}
					</p>
					<div class="flex justify-center rounded-5 bg-surface-alpha-gray-1 p-3.5 pb-2.5">
						<UpgradePicture name="shareBefore" :person="person" />
					</div>
				</div>
				<div class="mt-1 flex flex-col gap-2.5">
					<div class="text-xs font-semibold text-ink-blue-link">{{ __('Now') }}</div>
					<p class="text-p-base text-ink-gray-5">
						<span class="font-semibold text-ink-gray-9">
							{{ __('People edit through the workbook.') }}
						</span>
						{{ __('Sharing a chart or dashboard only lets them read it.') }}
					</p>
					<div class="flex justify-center rounded-5 bg-surface-alpha-gray-1 p-3.5 pb-2.5">
						<UpgradePicture name="shareNow" :person="person" />
					</div>
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
				<!-- one height on every step, so the picture neither jumps nor leaves the
				     lower half of the step empty -->
				<div
					v-if="picture"
					class="flex h-[220px] shrink-0 items-center justify-center rounded-5 bg-surface-alpha-gray-1 p-2.5"
				>
					<UpgradePicture
						:name="picture"
						:person="person"
						:doctype="current?.item.data?.doctypes?.[0]"
					/>
				</div>

				<div
					v-if="current && sentence"
					class="flex flex-col gap-3 rounded-5 border border-outline-gray-2 bg-surface-base px-4 py-3.5 shadow-sm"
					aria-live="polite"
				>
					<div class="flex items-center gap-2.5 text-xs text-ink-gray-5 tabular-nums">
						<span>{{
							__('{0} of {1}', String(handled + 1), String(rows.length))
						}}</span>
						<div
							class="h-1 max-w-[120px] flex-1 overflow-hidden rounded-1 bg-surface-gray-3"
						>
							<div
								class="h-full rounded-1 bg-surface-blue-7"
								:style="{ width: `${Math.round((handled / rows.length) * 100)}%` }"
							/>
						</div>
					</div>
					<p class="text-p-md text-ink-gray-6">
						<UpgradeSentence :parts="sentence.text" />
					</p>
					<div
						v-if="sentence.todo"
						class="-mt-1 flex items-center gap-2 text-p-base font-medium text-ink-gray-8"
					>
						<span
							class="grid size-5 shrink-0 place-items-center rounded-full bg-surface-blue-2 text-ink-blue-7"
						>
							<ArrowRight class="size-3" stroke-width="2" />
						</span>
						<span><UpgradeSentence :parts="sentence.todo" /></span>
					</div>
					<div class="flex items-center gap-2">
						<Button
							v-if="
								sentence.action &&
								(sentence.action.kind !== 'fix' || current.item.can_fix)
							"
							variant="subtle"
							@click="openAction(sentence.action)"
						>
							{{ sentence.action.label }}
							<template v-if="sentence.action.kind === 'form'" #suffix>
								<ExternalLink class="size-3.5 text-ink-gray-7" stroke-width="1.5" />
							</template>
						</Button>
						<span class="flex-1" />
						<Button
							variant="ghost"
							:label="__('Skip')"
							@click="upgrade.skip(current.item.name)"
						/>
						<Button
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

				<div
					v-else
					class="flex flex-col gap-3 rounded-5 border border-dashed border-outline-gray-2 bg-surface-gray-1 px-4 py-3.5"
				>
					<p class="text-p-md text-ink-gray-8">
						{{
							skippedCount === 0
								? __('All done here.')
								: skippedCount === 1
								  ? __('1 skipped. It stays in your list for later.')
								  : __(
											'{0} skipped. They stay in your list for later.',
											String(skippedCount),
								    )
						}}
					</p>
					<div v-if="skippedCount">
						<Button
							variant="subtle"
							:label="__('Go through skipped')"
							@click="upgrade.unskip(rows.map((row) => row.item.name))"
						/>
					</div>
				</div>

				<div
					v-if="doneCount || skippedCount"
					class="-mt-1.5 flex items-center gap-1 text-xs text-ink-gray-5"
				>
					<template v-if="doneCount">
						<Check class="size-3 text-ink-green-7" stroke-width="2" />
						{{ __('{0} done', String(doneCount)) }}
					</template>
					<template v-if="doneCount && skippedCount"> · </template>
					<template v-if="skippedCount">{{
						__('{0} skipped', String(skippedCount))
					}}</template>
				</div>
			</template>
		</div>

		<div class="flex items-center gap-2 border-t border-outline-gray-1 py-3 pl-6 pr-5">
			<Button v-if="!firstScreen" variant="ghost" :label="__('Back')" @click="back">
				<template #prefix><ArrowLeft class="size-4" stroke-width="1.5" /></template>
			</Button>
			<span class="flex-1" />
			<Button
				v-if="group && current"
				variant="subtle"
				:label="__('Later')"
				:tooltip="__('The rest stay in your list')"
				@click="next"
			/>
			<Button v-else data-primary variant="solid" @click="next">
				{{
					props.step.id === 'welcome' && !onLastSlide
						? __('Next')
						: group
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
