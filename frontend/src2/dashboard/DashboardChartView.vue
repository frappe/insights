<script setup lang="ts">
import { Button, Tooltip } from 'frappe-ui'
import { Pencil } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import ChartView from '../charts/ChartView.vue'
import { navigate } from '../helpers/navigation'
import { __ } from '../translation'
import { useChartCell, type ChartCellProps } from './chart_cell'
import TableCardActions from './TableCardActions.vue'

// A chart cell as a reader gets it: a read-only card. On a table, the reader can
// also filter and find rows.
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

// The card's popovers are teleported out of the hover group. While one is open,
// this keeps the actions row visible.
const actionsActive = ref(false)

// A reader who may edit the chart opens it in its workbook. The chart belongs to
// the workbook, not the dashboard, so this leaves the page. It shows on hover,
// like on the builder card.
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
		<!-- hidden until hover, like the card's other actions. The card reveals
		     them, and the expanded dialog renders outside the card -->
		<template v-if="chartRoute" #hoverActions>
			<Tooltip :text="__('Edit Chart')">
				<Button variant="ghost" @click="navigate(chartRoute)">
					<Pencil class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
				</Button>
			</Tooltip>
		</template>
	</ChartView>
</template>
