<script setup lang="ts">
import ChartView from '../charts/ChartView.vue'
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
</script>

<template>
	<ChartView :chart="read" :reading="reading" :filtered="filtered" @reset-filters="resetFilters">
		<template v-if="isTable" #actions>
			<TableCardActions
				v-model:filters="cardFilters"
				v-model:find-text="findText"
				v-model:find-open="findOpen"
				:columns="columns"
				:values-provider="valuesProvider"
				:range-provider="rangeProvider"
			/>
		</template>
	</ChartView>
</template>
