<script setup lang="ts">
import { Button, Tooltip } from 'frappe-ui'
import { Pencil } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { rendersOwnCards } from '../charts/adapter'
import ChartRenderer from '../charts/components/ChartRenderer.vue'
import { __ } from '../translation'
import { useChartCell, type ChartCellProps } from './chart_cell'
import CardActions from './CardActions.vue'

// A chart cell in the builder. Sorting writes the chart's config, and a drill
// opens in the query builder.
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

const actionsActive = ref(false)
// a card that renders itself heads its title with a zero-height row, which fits the smallest control
const actionSize = computed(() =>
	read.value && rendersOwnCards(read.value.doc.chart_type) ? 'xs' : 'sm',
)

// Editing a chart is not editing the dashboard. The chart is a workbook object
// and the dashboard only names it, so the action sits on the card and never
// touches the layout state.
const chartRoute = computed(() =>
	props.item.chart ? props.dashboard.chartRoute?.(props.item.chart) : undefined,
)
</script>

<template>
	<ChartRenderer
		:chart="read"
		:reading="reading"
		:actions-revealed="actionsActive"
		:filtered="filtered"
		@reset-filters="resetFilters"
	>
		<template v-if="isTable || filterable" #actions="{ expanded }">
			<CardActions
				v-model:filters="cardFilters"
				v-model:find-text="findText"
				v-model:find-open="findOpen"
				v-model:active="actionsActive"
				:filterable="filterable"
				:findable="isTable"
				:columns="columns"
				:values-provider="valuesProvider"
				:range-provider="rangeProvider"
				:reveal="!expanded"
			/>
		</template>
		<template v-if="chartRoute" #hoverActions>
			<Tooltip :text="__('Edit Chart')">
				<Button variant="ghost" :size="actionSize" :route="chartRoute">
					<Pencil class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
				</Button>
			</Tooltip>
		</template>
	</ChartRenderer>
</template>
