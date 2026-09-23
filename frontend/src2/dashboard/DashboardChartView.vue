<script setup lang="ts">
import { Button, Tooltip } from 'frappe-ui'
import { Pencil } from 'lucide-vue-next'
import { computed, ref } from 'vue'
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
	filterable,
	cardFilters,
	valuesProvider,
	rangeProvider,
	findText,
	findOpen,
} = useChartCell(props)

// A popover this card opens is portaled out of the hover group, so the acts row
// says it is still in use while one is up.
const actionsActive = ref(false)

// A reader who may edit the chart jumps to it in its workbook. The chart is a
// workbook object and the dashboard only names it, so this is a way out of the
// page, drawn on hover like the builder card's.
const chartRoute = computed(() =>
	props.item.chart ? props.dashboard.chartRoute?.(props.item.chart) : undefined,
)
</script>

<template>
	<ChartView
		:chart="read"
		:reading="reading"
		:filtered="filtered"
		:actions-revealed="actionsActive"
		@reset-filters="resetFilters"
	>
		<template v-if="isTable" #actions>
			<TableCardActions
				v-model:filters="cardFilters"
				v-model:find-text="findText"
				v-model:find-open="findOpen"
				v-model:active="actionsActive"
				:filterable="filterable"
				:columns="columns"
				:values-provider="valuesProvider"
				:range-provider="rangeProvider"
			/>
		</template>
		<!-- hidden until the card is pointed at, like every other act on it: the
		     card is what reveals them, and the expanded dialog is drawn outside it -->
		<template v-if="chartRoute" #hoverActions>
			<Tooltip :text="__('Edit Chart')">
				<Button variant="ghost" @click="navigate(chartRoute)">
					<Pencil class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
				</Button>
			</Tooltip>
		</template>
	</ChartView>
</template>
