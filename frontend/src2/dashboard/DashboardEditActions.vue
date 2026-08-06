<script setup lang="ts">
import { Edit3, Share2 } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import { __ } from '../translation'
import type { WorkbookChart } from '../types/workbook.types'
import type { Dashboard } from './dashboard'
import DashboardChartSelectorDialog from './DashboardChartSelectorDialog.vue'
import DashboardShareDialog from './DashboardShareDialog.vue'
import { chartOptionsKey } from './authoring'

// What the page offers to whoever may write it. The page draws this next to the
// actions everyone gets, and draws nothing here for a reader who holds no
// authoring feed.
const dashboard = inject('dashboard') as Dashboard
const charts = inject(chartOptionsKey, [] as WorkbookChart[])

const showChartSelectorDialog = ref(false)
const showShareDialog = ref(false)
</script>

<template>
	<Button
		v-if="!dashboard.editing && !dashboard.doc.read_only"
		variant="ghost"
		:label="__('Share')"
		@click="showShareDialog = true"
	>
		<template #prefix>
			<Share2 class="h-4 text-ink-gray-6" stroke-width="1.5" />
		</template>
	</Button>
	<Button
		v-if="!dashboard.editing"
		variant="ghost"
		:label="__('Edit')"
		@click="dashboard.editing = true"
	>
		<template #prefix>
			<Edit3 class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
		</template>
	</Button>

	<template v-if="dashboard.editing">
		<Button variant="outline" icon-left="plus" @click="showChartSelectorDialog = true">
			{{ __('Chart') }}
		</Button>
		<Button variant="outline" icon-left="plus" @click="() => dashboard.addFilter()">
			{{ __('Filter') }}
		</Button>
		<Button variant="outline" icon-left="plus" @click="() => dashboard.addText()">
			{{ __('Text') }}
		</Button>
		<Button
			variant="solid"
			icon-left="check"
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
