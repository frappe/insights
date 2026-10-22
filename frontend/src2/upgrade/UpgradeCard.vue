<script setup lang="ts">
import { SidebarCard } from 'frappe-ui'
import { Sparkle } from 'lucide-vue-next'
import { computed, watch } from 'vue'
import session from '../session'
import { __ } from '../translation'
import upgrade from './upgrade'
import { cardDescription } from './upgrade_steps'

// Where the wizard is picked up again: the step it was left at, or what is
// left once it was finished.
watch(
	() => session.initialized && session.user.upgrade_item_count > 0 && !upgrade.loaded,
	(due) => due && upgrade.load(),
	{ immediate: true },
)

const progress = computed(() => upgrade.progress)
const left = computed(() => upgrade.openWizardItems.length)

const unfinished = computed(() => progress.value.started && !progress.value.finished)
const show = computed(() => !upgrade.showWizard && (unfinished.value || left.value > 0))

const description = computed(() =>
	cardDescription(
		left.value,
		unfinished.value ? { index: upgrade.stepIndex, count: upgrade.steps.length } : undefined,
	),
)

const percent = computed(() => {
	if (!left.value) {
		return Math.round((upgrade.stepIndex / Math.max(1, upgrade.steps.length - 1)) * 100)
	}
	const total = upgrade.steps.reduce((n, step) => n + ('rows' in step ? step.rows.length : 0), 0)
	return Math.round(((total - left.value) / Math.max(1, total)) * 100)
})
</script>

<template>
	<SidebarCard v-if="show">
		<template #prefix><Sparkle class="size-4 text-ink-gray-8" stroke-width="1.5" /></template>
		<template #title>{{ __('Insights 3.50') }}</template>
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
