<script setup lang="ts">
import {
	SettingsContent,
	SettingsDialog,
	SettingsNavGroup,
	SettingsNavItem,
	SettingsPanel,
	SettingsSidebar,
} from 'frappe-ui'
import { Check, Sparkle } from 'lucide-vue-next'
import { computed, watch } from 'vue'
import session from '../session'
import { __ } from '../translation'
import upgrade from './upgrade'
import UpgradeStepView from './UpgradeStepView.vue'
import type { Step } from './upgrade_steps'

// The upgrade to Insights v3.50, one step at a time: a welcome, each thing that is
// new, then each group of items that needs the reader. It opens once by
// itself; the sidebar card resumes it where the reader left it.
watch(
	() => session.initialized && session.user.upgrade_unseen,
	(upgraded) => upgraded && upgrade.open(),
	{ immediate: true },
)

const show = computed({
	get: () => upgrade.showWizard,
	set: (value) => !value && upgrade.close(),
})

const steps = computed(() => upgrade.steps)
const step = computed(() => steps.value[upgrade.stepIndex])
const tab = computed({
	get: () => step.value?.id,
	set: (id) => id && upgrade.goTo(String(id)),
})

const sectionLabels = {
	welcome: undefined,
	new: __("What's new"),
	upgrade: __('Your upgrade'),
}

const openCount = (step: Step) =>
	'rows' in step ? step.rows.filter((row) => !row.names.every(upgrade.isDone)).length : 0

function state(step: Step) {
	if ('rows' in step) {
		if (!openCount(step)) return 'done'
		return step.group.kind === 'now' ? 'now' : 'open'
	}
	const seen = upgrade.progress.seen.includes(step.id) && step.id !== tab.value
	return seen ? 'done' : 'open'
}
</script>

<template>
	<SettingsDialog
		v-if="upgrade.loaded"
		v-model:open="show"
		v-model:tab="tab"
		size="5xl"
		:keyboard-shortcut="false"
	>
		<template #title>{{ __('Insights v3.50') }}</template>
		<template #description>{{ __('What is new, and what the upgrade left for you') }}</template>
		<SettingsSidebar>
			<div class="flex items-center gap-2 px-1.5 pb-1 pt-2">
				<span class="grid size-[26px] place-items-center rounded-4 bg-surface-gray-2">
					<Sparkle class="size-4 text-ink-gray-8" stroke-width="1.5" />
				</span>
				<span class="text-base font-semibold text-ink-gray-9">{{
					__('Insights v3.50')
				}}</span>
			</div>
			<template v-for="section in ['welcome', 'new', 'upgrade'] as const" :key="section">
				<SettingsNavGroup
					v-if="steps.some((s) => s.section === section)"
					:label="sectionLabels[section]"
				>
					<SettingsNavItem
						v-for="item in steps.filter((s) => s.section === section)"
						:key="item.id"
						:value="item.id"
					>
						<template #prefix>
							<span
								v-if="state(item) === 'done'"
								class="grid size-4 shrink-0 place-items-center rounded-full bg-surface-green-10"
							>
								<Check class="size-2.5 text-ink-base" stroke-width="3" />
							</span>
							<span
								v-else
								class="size-4 shrink-0 rounded-full border-[1.5px]"
								:class="
									state(item) === 'now'
										? 'border-outline-amber-4'
										: 'border-outline-gray-3'
								"
							/>
						</template>
						{{ item.label }}
						<template v-if="'rows' in item" #suffix>
							<span class="text-sm tabular-nums text-ink-gray-5">
								{{ openCount(item) || '' }}
							</span>
						</template>
					</SettingsNavItem>
				</SettingsNavGroup>
			</template>
		</SettingsSidebar>
		<!-- frappe-ui's content and panel take their content's width, so a long
		     name in a picture would push the step past the dialog's edge -->
		<SettingsContent data-upgrade-wizard class="min-w-0">
			<SettingsPanel v-if="step" :value="step.id" class="min-w-0">
				<UpgradeStepView :key="step.id" :step="step" @close="show = false" />
			</SettingsPanel>
		</SettingsContent>
	</SettingsDialog>
</template>

<style>
/* frappe-ui's SettingsDialog grows with the window up to 860px and has no height prop */
@media (min-width: 640px) {
	[data-slot='content'] > div:has(> [data-upgrade-wizard]) {
		height: min(704px, calc(100vh - 6rem));
	}
}
</style>
