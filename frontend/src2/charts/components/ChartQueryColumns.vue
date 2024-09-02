<script setup lang="ts">
import { Edit, Plus, X } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import DataTypeIcon from '../../query/components/DataTypeIcon.vue'
import NewColumnSelectorDialog from '../../query/components/NewColumnSelectorDialog.vue'
import { ExpressionMeasure, MeasureDataType, MutateArgs } from '../../types/query.types'
import { Chart } from '../chart'

const chart = inject('chart') as Chart
const showNewColumnSelectorDialog = ref(false)

const activeEditMeasure = ref<ExpressionMeasure>()
function setActiveEditMeasure(measure: ExpressionMeasure) {
	activeEditMeasure.value = measure
	showNewColumnSelectorDialog.value = true
}
function toMutateArgs(measure: ExpressionMeasure): MutateArgs {
	return {
		new_name: measure.measure_name,
		expression: measure.expression,
		data_type: measure.data_type,
	}
}

function updateMeasure(args: MutateArgs) {
	const measure = {
		measure_name: args.new_name,
		expression: args.expression,
		data_type: args.data_type as MeasureDataType,
	}
	if (!activeEditMeasure.value) {
		chart.baseQuery.addMeasure(measure)
	} else {
		chart.baseQuery.updateMeasure(activeEditMeasure.value.measure_name, measure)
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
			class="flex h-7 cursor-grab items-center gap-2 rounded px-1 text-gray-700 hover:bg-gray-100"
		>
			<DataTypeIcon :column-type="dimension.data_type" />
			<span class="flex-1 truncate">{{ dimension.column_name }}</span>
		</div>
		<hr class="my-2 border-t border-gray-200" />
		<div
			v-for="measure in chart.baseQuery.measures"
			:key="measure.measure_name"
			class="group flex h-7 cursor-grab items-center gap-2 rounded px-1 text-gray-700 hover:bg-gray-100"
		>
			<DataTypeIcon :column-type="measure.data_type" />
			<span class="flex-1 truncate">{{ measure.measure_name }}</span>
			<div class="invisible ml-auto flex-shrink-0 group-hover:visible">
				<button
					v-if="'expression' in measure"
					class="group cursor-pointer p-1"
					@click.prevent.stop="setActiveEditMeasure(measure)"
				>
					<Edit
						class="h-3.5 w-3.5 text-gray-500 transition-all group-hover:text-gray-700"
						stroke-width="1.5"
					/>
				</button>
				<button
					v-if="'expression' in measure"
					class="group cursor-pointer p-1"
					@click.prevent.stop="chart.baseQuery.removeMeasure(measure.measure_name)"
				>
					<X
						class="h-3.5 w-3.5 text-gray-500 transition-all group-hover:text-gray-700"
						stroke-width="1.5"
					/>
				</button>
			</div>
		</div>
	</div>

	<NewColumnSelectorDialog
		v-if="showNewColumnSelectorDialog"
		v-model="showNewColumnSelectorDialog"
		:mutation="activeEditMeasure ? toMutateArgs(activeEditMeasure) : undefined"
		@select="updateMeasure"
	/>
</template>
