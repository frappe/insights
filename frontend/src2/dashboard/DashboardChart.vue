<script setup lang="ts">
import { Button, Tooltip } from 'frappe-ui'
import { AlertTriangle, Pencil } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import ChartRenderer from '../charts/components/ChartRenderer.vue'
import { __ } from '../translation'
import { useChartCell, type ChartCellProps } from './chart_cell'
import TableCardActions from './TableCardActions.vue'

// A chart cell in the builder: the card its owner can change. Sorting writes the
// chart's config, and the drill opens into the query builder.
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

const actionsActive = ref(false)

// Editing a chart is not editing the dashboard. The chart is a workbook object
// and the dashboard only names it, so the action sits on the card and never
// touches the layout state.
const chartRoute = computed(() =>
	props.item.chart ? props.dashboard.builder?.chartRoute(props.item.chart) : undefined,
)
</script>

<template>
	<ChartRenderer
		v-if="read"
		:chart="read"
		:reading="reading"
		:actions-revealed="actionsActive"
		:filtered="filtered"
		@reset-filters="resetFilters"
	>
		<template v-if="isTable" #actions="{ expanded }">
			<TableCardActions
				v-model:filters="cardFilters"
				v-model:find-text="findText"
				v-model:find-open="findOpen"
				v-model:active="actionsActive"
				:columns="columns"
				:values-provider="valuesProvider"
				:range-provider="rangeProvider"
				:reveal="!expanded"
			/>
		</template>
		<template v-if="chartRoute" #hoverActions>
			<Tooltip :text="__('Edit Chart')">
				<Button variant="ghost" :route="chartRoute">
					<Pencil class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
				</Button>
			</Tooltip>
		</template>
	</ChartRenderer>

	<!-- not one of the card's states: a grid item that names no chart has no store
	     to be loading, failed or empty. It is the layout that is wrong, not a read. -->
	<div
		v-else
		class="flex h-full flex-1 flex-col items-center justify-center rounded-4 border border-outline-gray-2"
	>
		<div class="flex items-center gap-1.5 text-p-base text-ink-gray-4">
			<AlertTriangle class="h-3.5 w-3.5 shrink-0 text-ink-red-5" stroke-width="1.5" />
			<span>{{ __('Chart not found') }}</span>
		</div>
	</div>
</template>
