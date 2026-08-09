<script setup lang="ts">
import { Button } from 'frappe-ui'
import { Maximize, XIcon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { Query } from '../../query/query'
import { ChartRead } from '../chart_read'
import ChartBody from './ChartBody.vue'
import DrillDown from './DrillDown.vue'

// The chart with the affordances the builder and the SPA give it: expand, and
// drill down into the rows behind a segment. The chart itself is ChartBody.
const props = defineProps<{ chart: ChartRead; hideMaximize?: boolean }>()

const drillDownQuery = ref<Query>()
const showDrillDown = ref(false)
function openDrillDown(query: Query) {
	drillDownQuery.value = query
	showDrillDown.value = true
}

const showExpandedChartDialog = ref(false)
const canMaximize = computed(
	() => !props.hideMaximize && props.chart && props.chart.doc.chart_type !== 'Number',
)
</script>

<template>
	<div class="group relative h-full w-full">
		<ChartBody :chart="props.chart" @drill-down="openDrillDown" />

		<div
			v-if="canMaximize"
			class="absolute top-0 right-0 opacity-0 transition-opacity group-hover:opacity-100"
			:class="chart.doc.chart_type == 'Table' ? 'p-1.5' : 'p-2'"
		>
			<Button variant="ghost" @click="showExpandedChartDialog = true">
				<Maximize class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
			</Button>
		</div>
	</div>

	<DrillDown
		v-if="drillDownQuery"
		v-model="showDrillDown"
		@update:modelValue="!$event ? (drillDownQuery = undefined) : undefined"
		:query="drillDownQuery"
		:adhoc-filters="props.chart.routedFilters"
	>
	</DrillDown>

	<Dialog v-if="chart" v-model:open="showExpandedChartDialog" size="7xl" bare>
		<template #default>
			<div class="h-[85vh] w-full">
				<ChartBody :chart="props.chart" @drill-down="openDrillDown" />
				<div class="absolute top-2 right-2">
					<Button variant="ghost" @click="showExpandedChartDialog = false">
						<template #icon>
							<XIcon class="size-4 text-ink-gray-6" />
						</template>
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
