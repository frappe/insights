<script setup lang="ts">
import { Dialog, TabButtons } from 'frappe-ui'
import { Sparkles } from 'lucide-vue-next'
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { RouteLocationRaw, useRouter } from 'vue-router'
import session from '../session'
import { __ } from '../translation'
import { attentionGroups } from './needs_attention'
import upgrade, { UpgradeItem } from './upgrade'
import { whatsNewFor } from './whats_new'

const Settings = defineAsyncComponent(() => import('../settings/Settings.vue'))

const router = useRouter()

watch(
	() => session.initialized && session.user.upgraded_from_v3,
	(upgraded) => upgraded && upgrade.open('whats_new'),
	{ immediate: true },
)

const show = computed({
	get: () => upgrade.show,
	set: (value) => !value && upgrade.close(),
})

const sections = computed(() => whatsNewFor(session.user.is_admin))

const tabs = computed(() => [
	{ label: __("What's new"), value: 'whats_new' },
	{ label: __('Needs attention ({0})', String(upgrade.items.length)), value: 'attention' },
])
// the tab stays after the last fix, so the reader is not moved
const showTabs = computed(() => upgrade.tab === 'attention' || upgrade.items.length > 0)

const groups = computed(() => attentionGroups(upgrade.items))

const COLLAPSED_ITEMS = 5
const expanded = ref(new Set<string>())
// a Show all that reveals one item takes the place of that item
function shownItems(code: string, items: UpgradeItem[]) {
	if (expanded.value.has(code) || items.length <= COLLAPSED_ITEMS + 1) return items
	return items.slice(0, COLLAPSED_ITEMS)
}

const actions = computed(() => {
	const count = upgrade.items.length
	if (upgrade.tab === 'whats_new' && count) {
		return [
			{
				label: count === 1 ? __('Review 1 item') : __('Review {0} items', String(count)),
				variant: 'solid' as const,
				onClick: () => {
					upgrade.tab = 'attention'
				},
			},
		]
	}
	return [{ label: __('Done'), variant: 'solid' as const, onClick: () => upgrade.close() }]
})

const ROUTES: Record<string, (workbook: string, name: string) => RouteLocationRaw> = {
	'Insights Workbook': (workbook) => ({ name: 'Workbook', params: { workbook_name: workbook } }),
	'Insights Query v3': (workbook, name) => ({
		name: 'WorkbookQuery',
		params: { workbook_name: workbook, query_name: name },
	}),
	'Insights Chart v3': (workbook, name) => ({
		name: 'WorkbookChart',
		params: { workbook_name: workbook, chart_name: name },
	}),
	'Insights Dashboard v3': (workbook, name) => ({
		name: 'WorkbookDashboard',
		params: { workbook_name: workbook, dashboard_name: name },
	}),
}

function referenceRoute(item: UpgradeItem) {
	const route = item.workbook && ROUTES[item.reference_doctype ?? '']
	return route ? route(item.workbook!, item.reference_name!) : undefined
}

function openReference(item: UpgradeItem) {
	router.push(referenceRoute(item)!)
	upgrade.close()
}

const FIX_LABELS = {
	share_workbook: __('Share as editor'),
	delete_workbook: __('Delete copy'),
	open_settings: __('Open settings'),
}

const showSettings = ref(false)
const pending = ref<string | null>(null)

async function fix(item: UpgradeItem) {
	if (item.action === 'open_settings') {
		showSettings.value = true
		return
	}
	pending.value = item.name
	await upgrade.fix(item)
	pending.value = null
}

// a word in backticks is code
function parts(point: string) {
	return point.split('`').map((text, index) => ({ text, code: index % 2 === 1 }))
}
</script>

<template>
	<Dialog
		v-model:open="show"
		size="3xl"
		:title="__('Welcome to Insights 4')"
		:icon="Sparkles"
		theme="blue"
		:actions="actions"
	>
		<template #default>
			<div class="flex flex-col gap-5">
				<TabButtons
					v-if="showTabs"
					v-model="upgrade.tab"
					:options="tabs"
					class="self-start"
				/>

				<div
					v-if="upgrade.tab === 'whats_new'"
					class="flex max-h-[60vh] flex-col gap-6 overflow-y-auto"
				>
					<p class="text-p-base text-ink-gray-7">
						{{ __("Here's what changed since Insights 3.") }}
					</p>
					<section
						v-for="section in sections"
						:key="section.title"
						class="flex flex-col gap-2"
					>
						<h4 class="text-base-medium text-ink-gray-8">{{ section.title }}</h4>
						<ul
							class="flex list-disc flex-col gap-1.5 pl-5 text-p-base text-ink-gray-7"
						>
							<li v-for="point in section.points" :key="point">
								<template v-for="part in parts(point)">
									<code
										v-if="part.code"
										class="rounded-4 bg-surface-gray-2 px-1 font-mono text-p-sm text-ink-gray-8"
										>{{ part.text }}</code
									>
									<template v-else>{{ part.text }}</template>
								</template>
							</li>
						</ul>
					</section>
				</div>

				<div v-else class="flex max-h-[60vh] flex-col gap-6 overflow-y-auto">
					<p
						v-if="!upgrade.items.length"
						class="py-6 text-center text-p-base text-ink-gray-5"
					>
						{{ __('Nothing needs attention.') }}
					</p>
					<section v-for="group in groups" :key="group.code" class="flex flex-col gap-2">
						<div class="flex flex-col gap-1">
							<h4 class="text-base-medium text-ink-gray-8">
								{{ group.title }}
								<span class="text-ink-gray-5">· {{ group.items.length }}</span>
							</h4>
							<p v-if="group.description" class="text-p-sm text-ink-gray-6">
								{{ group.description }}
							</p>
						</div>
						<div
							class="divide-y divide-outline-gray-1 rounded-6 border border-outline-gray-2"
						>
							<div
								v-for="item in shownItems(group.code, group.items)"
								:key="item.name"
								class="flex items-center gap-4 py-1.5 pl-3 pr-1.5"
							>
								<p class="flex-1 text-p-base text-ink-gray-8">
									<template v-for="part in parts(item.message)">
										<code
											v-if="part.code"
											class="rounded-4 bg-surface-gray-2 px-1 font-mono text-p-sm text-ink-gray-8"
											>{{ part.text }}</code
										>
										<template v-else>{{ part.text }}</template>
									</template>
								</p>
								<div class="flex shrink-0 items-center gap-1.5">
									<Button
										v-if="referenceRoute(item)"
										variant="ghost"
										:label="__('Open')"
										@click="openReference(item)"
									/>
									<Button
										v-else-if="item.form_url"
										variant="ghost"
										:label="__('Open')"
										:href="item.form_url"
									/>
									<Button
										v-if="item.action && item.can_fix"
										:label="FIX_LABELS[item.action]"
										:loading="pending === item.name"
										@click="fix(item)"
									/>
									<Button
										variant="ghost"
										icon="lucide-x"
										:tooltip="__('Dismiss')"
										:aria-label="__('Dismiss')"
										@click="upgrade.dismiss(item)"
									/>
								</div>
							</div>
						</div>
						<Button
							v-if="shownItems(group.code, group.items).length < group.items.length"
							variant="ghost"
							class="self-start"
							:label="__('Show all {0}', String(group.items.length))"
							@click="expanded.add(group.code)"
						/>
					</section>
				</div>
			</div>
		</template>
	</Dialog>

	<Settings v-if="showSettings" v-model="showSettings" :tab="__('General')" />
</template>
