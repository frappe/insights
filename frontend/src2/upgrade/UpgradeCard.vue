<script setup lang="ts">
import { SidebarCard } from 'frappe-ui'
import { Sparkle } from 'lucide-vue-next'
import { computed, watch } from 'vue'
import session from '../session'
import { __ } from '../translation'
import upgrade from './upgrade'
import { needsYou } from './upgrade_steps'

// Where the wizard is picked up again: the step it was left at, or what is
// left once it was finished.
watch(
	() => session.initialized && session.user.upgrade_item_count > 0 && !upgrade.loaded,
	(due) => due && upgrade.load(),
	{ immediate: true },
)

const progress = computed(() => upgrade.progress)
const left = computed(() => upgrade.openWizardItems.length)
const now = computed(() => upgrade.openWizardItems.filter((row) => needsYou(row.item)).length)

const unfinished = computed(() => progress.value.started && !progress.value.finished)
const show = computed(() => !upgrade.showWizard && (unfinished.value || left.value > 0))

const description = computed(() => {
	if (unfinished.value) {
		return __('Step {0} of {1}', String(upgrade.stepIndex + 1), String(upgrade.steps.length))
	}
	if (!left.value) return __('All done')
	return now.value
		? __('{0} left, {1} need you now', String(left.value), String(now.value))
		: __('{0} left', String(left.value))
})

const percent = computed(() => {
	if (unfinished.value) {
		return Math.round((upgrade.stepIndex / Math.max(1, upgrade.steps.length - 1)) * 100)
	}
	const total = upgrade.steps.reduce((n, step) => n + ('rows' in step ? step.rows.length : 0), 0)
	return Math.round(((total - left.value) / Math.max(1, total)) * 100)
})
</script>

<template>
	<SidebarCard v-if="show">
		<template #prefix><Sparkle class="size-4 text-ink-gray-8" stroke-width="1.5" /></template>
		<template #title>{{ __('Insights v4') }}</template>
		<template #description>
			<span class="flex flex-col gap-1.5">
				<span>{{ description }}</span>
				<span
					v-if="unfinished || left"
					class="block h-1 overflow-hidden rounded-1 bg-surface-gray-2"
				>
					<span
						class="block h-full rounded-1 bg-surface-gray-10"
						:style="{ width: `${percent}%` }"
					/>
				</span>
			</span>
		</template>
		<template #actions>
			<Button
				v-if="unfinished || left"
				variant="subtle"
				size="sm"
				class="w-full"
				:label="unfinished ? __('Resume') : __('Review')"
				@click="upgrade.resume()"
			/>
		</template>
	</SidebarCard>
</template>
