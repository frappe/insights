<script setup lang="ts">
import { TabButtons } from 'frappe-ui'
import { Edit3, Share2 } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import { __ } from '../translation'
import type { WorkbookChart } from '../types/workbook.types'
import { chartOptionsKey } from './builder'
import type { Dashboard } from './dashboard'
import DashboardChartSelectorDialog from './DashboardChartSelectorDialog.vue'
import DashboardShareDialog from './DashboardShareDialog.vue'
import { BREAKPOINTS } from './grid_placement'

// Actions for a user who may write the dashboard. Only the builder renders
// them, next to the actions every reader gets.
const dashboard = inject('dashboard') as Dashboard
const charts = inject(chartOptionsKey, [] as WorkbookChart[])

const showChartSelectorDialog = ref(false)
const showShareDialog = ref(false)

// Widest first, because the owner arranges the widest layout first. Built from
// `BREAKPOINTS`, so a new breakpoint shows up here without a change.
//
// The label is the tooltip. The switcher renders `title` from the label of an
// option with an icon, and ignores a `tooltip` key.
const widths = computed(() =>
	[...BREAKPOINTS].reverse().map((breakpoint) => ({
		value: breakpoint.key,
		icon: breakpoint.icon,
		label: __(breakpoint.label),
	})),
)
</script>

<template>
	<Button
		v-if="!dashboard.editing && dashboard.doc.can_share"
		variant="outline"
		:label="__('Share')"
		@click="showShareDialog = true"
	>
		<template #prefix>
			<Share2 class="h-4 text-ink-gray-6" stroke-width="1.5" />
		</template>
	</Button>
	<Button
		v-if="!dashboard.editing"
		variant="outline"
		:label="__('Edit')"
		@click="dashboard.editing = true"
	>
		<template #prefix>
			<Edit3 class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
		</template>
	</Button>

	<template v-if="dashboard.editing">
		<TabButtons v-model="dashboard.arranging" :options="widths" />
		<Button variant="outline" icon-left="lucide-plus" @click="showChartSelectorDialog = true">
			{{ __('Chart') }}
		</Button>
		<Button variant="outline" icon-left="lucide-plus" @click="() => dashboard.addFilter()">
			{{ __('Filter') }}
		</Button>
		<Button variant="outline" icon-left="lucide-plus" @click="() => dashboard.addText()">
			{{ __('Text') }}
		</Button>
		<Button
			variant="solid"
			icon-left="lucide-check"
			:loading="dashboard.saving"
			@click="dashboard.finishEditing()"
		>
			{{ __('Done') }}
		</Button>
	</template>

	<DashboardChartSelectorDialog v-model="showChartSelectorDialog" :chartOptions="charts" />

	<DashboardShareDialog v-if="showShareDialog" v-model="showShareDialog" />
</template>
