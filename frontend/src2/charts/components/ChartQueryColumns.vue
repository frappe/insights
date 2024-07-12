<script setup lang="ts">
import { inject } from 'vue'
import { Chart } from '../chart'
import { Plus } from 'lucide-vue-next'
import DataTypeIcon from '../../query/components/DataTypeIcon.vue'

const chart = inject('chart') as Chart
</script>

<template>
	<div v-if="chart.doc.query">
		<div class="flex items-center justify-between">
			<label class="inline-flex flex-shrink-0 text-xs leading-7 text-gray-700">Columns</label>
			<div>
				<button class="cursor-pointer rounded p-1 transition-colors hover:bg-gray-100">
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
</template>
