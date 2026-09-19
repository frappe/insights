<script setup lang="ts">
import { Button, Tooltip } from 'frappe-ui'
import { Pencil } from 'lucide-vue-next'
import { computed } from 'vue'
import ChartView from '../charts/ChartView.vue'
import { navigate } from '../helpers/navigation'
import { __ } from '../translation'
import { useChartCell, type ChartCellProps } from './chart_cell'
import TableCardActions from './TableCardActions.vue'

// A chart cell as a reader gets it: the read-only card, and the reader's own
// filter and find on a table's rows.
const props = defineProps<ChartCellProps>()

const {
	read,
	reading,
	isTable,
	columns,
	filtered,
	resetFilters,
	cardFilters,
	valuesProvider,
	rangeProvider,
	findText,
	findOpen,
} = useChartCell(props)

// A reader who may edit the chart jumps to it in its workbook. The chart is a
// workbook object and the dashboard only names it, so this is a way out of the
// page, drawn on hover like the builder card's.
const chartRoute = computed(() =>
	props.item.chart ? props.dashboard.chartRoute?.(props.item.chart) : undefined,
)
</script>

<template>
	<ChartView :chart="read" :reading="reading" :filtered="filtered" @reset-filters="resetFilters">
		<template v-if="isTable || chartRoute" #actions>
			<div class="flex items-center gap-1">
				<TableCardActions
					v-if="isTable"
					v-model:filters="cardFilters"
					v-model:find-text="findText"
					v-model:find-open="findOpen"
					:columns="columns"
					:values-provider="valuesProvider"
					:range-provider="rangeProvider"
				/>
				<div
					v-if="chartRoute"
					class="w-0 overflow-hidden group-focus-within:w-auto group-focus-within:overflow-visible group-hover:w-auto group-hover:overflow-visible"
				>
					<Tooltip :text="__('Edit Chart')">
						<Button variant="ghost" @click="navigate(chartRoute)">
							<Pencil class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
						</Button>
					</Tooltip>
				</div>
			</div>
		</template>
	</ChartView>
</template>
