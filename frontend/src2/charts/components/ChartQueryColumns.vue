<script setup lang="ts">
import { Plus } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import DataTypeIcon from '../../query/components/DataTypeIcon.vue'
import NewColumnSelectorDialog from '../../query/components/NewColumnSelectorDialog.vue'
import { ExpressionMeasure, MeasureDataType, MutateArgs } from '../../types/query.types'
import { Chart } from '../chart'

const chart = inject('chart') as Chart
const showNewColumnSelectorDialog = ref(false)
function toMeasure(args: MutateArgs): ExpressionMeasure {
	return {
		column_name: args.new_name,
		expression: args.expression.expression,
		data_type: args.data_type as MeasureDataType,
	}
}
</script>

<template>
	<div v-if="chart.doc.query">
		<div class="flex items-center justify-between">
			<label class="inline-flex flex-shrink-0 text-xs leading-7 text-gray-700">Columns</label>
			<div>
				<button
					class="cursor-pointer rounded p-1 transition-colors hover:bg-gray-100"
					@click="showNewColumnSelectorDialog = true"
				>
					<Plus class="h-4 w-4 text-gray-700" stroke-width="1.5" />
				</button>
			</div>
		</div>
		<div
			v-for="dimension in chart.baseQuery.dimensions"
			:key="dimension.column_name"
			class="flex h-7 cursor-grab items-center gap-2 rounded px-1 hover:bg-gray-100"
		>
			<DataTypeIcon :column-type="dimension.data_type" />
			{{ dimension.column_name }}
		</div>
		<hr class="my-2 border-t border-gray-200" />
		<div
			v-for="measure in chart.baseQuery.measures"
			:key="measure.column_name"
			class="flex h-7 cursor-grab items-center gap-2 rounded px-1 hover:bg-gray-100"
		>
			<DataTypeIcon :column-type="measure.data_type" />
			{{ measure.column_name }}
		</div>
	</div>

	<NewColumnSelectorDialog
		v-if="showNewColumnSelectorDialog"
		v-model="showNewColumnSelectorDialog"
		:mutation="undefined"
		@select="chart.baseQuery.addMeasure(toMeasure($event))"
	/>
</template>
