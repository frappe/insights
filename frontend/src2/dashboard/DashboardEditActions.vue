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

// What the page offers to whoever may write it. The builder draws this next to
// the actions everyone gets, and no other surface draws it at all.
const dashboard = inject('dashboard') as Dashboard
const charts = inject(chartOptionsKey, [] as WorkbookChart[])

const showChartSelectorDialog = ref(false)
const showShareDialog = ref(false)

// One entry per breakpoint, widest first — the layout an owner arranges first
// reads first. A new width is a row in `BREAKPOINTS` and turns up here on its
// own, so this switch cannot fall behind the layouts the grid can draw.
//
// The label is the tooltip: the switcher renders `title` from the label of any
// option that carries an icon, so a `tooltip` of its own never reaches the DOM.
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
		v-if="!dashboard.editing && !dashboard.doc.read_only"
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
			@click="
				() => {
					dashboard.save()
					dashboard.editing = false
				}
			"
		>
			{{ __('Done') }}
		</Button>
	</template>

	<DashboardChartSelectorDialog v-model="showChartSelectorDialog" :chartOptions="charts" />

	<DashboardShareDialog v-if="showShareDialog" v-model="showShareDialog" />
</template>
