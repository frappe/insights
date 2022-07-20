<template>
	<div class="mb-4 flex h-7 items-center">
		<Button icon="chevron-left" class="mr-2" @click="$emit('close')"> </Button>
		<div class="text-lg font-medium">Add {{ newColumnType }}</div>
	</div>
	<div class="flex flex-col space-y-3">
		<div class="flex h-9 items-center space-x-2 rounded-md border bg-gray-50 p-0.5 text-sm">
			<div
				v-for="tab in ['Dimension', 'Metric', 'Expression']"
				class="flex h-full flex-1 items-center justify-center rounded-md"
				:class="{ 'border bg-white font-normal shadow-sm': newColumnType == tab }"
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
import MetricPicker from '@/components/Query/MetricPicker.vue'
import DimensionPicker from '@/components/Query/DimensionPicker.vue'
import ColumnExpressionPicker from '@/components/Query/ColumnExpressionPicker.vue'

import { inject, ref } from 'vue'

const query = inject('query')
const newColumnType = ref('Dimension')

const emit = defineEmits(['close'])
const addColumn = (column) => {
	query.addColumn({ column })
	emit('close')
}
</script>
