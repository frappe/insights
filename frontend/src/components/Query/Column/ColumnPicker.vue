<template>
	<div class="sticky top-0 z-10 flex items-center bg-white pb-3 pt-1">
		<Button icon="chevron-left" class="mr-2" @click="$emit('close')"> </Button>
		<div class="text-sm tracking-wide text-gray-600">ADD {{ newColumnType.toUpperCase() }}</div>
	</div>
	<div class="flex flex-col space-y-3">
		<div
			class="flex h-9 cursor-pointer items-center space-x-2 rounded-md bg-gray-100 p-1 text-sm"
		>
			<div
				v-for="tab in ['Dimension', 'Metric', 'Expression']"
				class="flex h-full flex-1 items-center justify-center rounded"
				:class="{
					' bg-white font-normal shadow': newColumnType == tab,
				}"
				@click.prevent.stop="newColumnType = tab"
			>
				{{ tab }}
			</div>
		</div>
		<MetricPicker v-if="newColumnType == 'Metric'" @column-select="addColumn" />
		<DimensionPicker v-if="newColumnType == 'Dimension'" @column-select="addColumn" />
		<ColumnExpressionPicker v-if="newColumnType == 'Expression'" @column-select="addColumn" />
	</div>
</template>

<script setup>
import MetricPicker from '@/components/Query/Column/MetricPicker.vue'
import DimensionPicker from '@/components/Query/Column/DimensionPicker.vue'
import ColumnExpressionPicker from '@/components/Query/Column/ColumnExpressionPicker.vue'

import { inject, ref } from 'vue'

const query = inject('query')
const newColumnType = ref('Dimension')

const emit = defineEmits(['close'])
const addColumn = (column) => {
	query.addColumn.submit({ column })
	emit('close')
}
</script>
