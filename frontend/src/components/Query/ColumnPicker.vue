<template>
	<div class="mb-4 flex h-7 items-center">
		<Button icon="chevron-left" class="mr-2" @click="$emit('close')"> </Button>
		<div class="text-lg font-medium">Add {{ newColumnType }}</div>
	</div>
	<div class="flex flex-col space-y-3">
		<div class="flex h-9 items-center space-x-2 rounded-md border bg-gray-50 p-0.5 text-sm">
			<div
				v-for="tab in ['Metric', 'Dimension', 'Expression']"
				class="flex h-full flex-1 items-center justify-center rounded-md"
				:class="{ 'border bg-white font-normal shadow-sm': newColumnType == tab }"
				@click.prevent.stop="newColumnType = tab"
			>
				{{ tab }}
			</div>
		</div>
		<MetricPicker
			v-if="newColumnType == 'Metric'"
			@column-select="(column) => query.addColumn({ column })"
		/>
		<DimensionPicker
			v-if="newColumnType == 'Dimension'"
			@column-select="(column) => query.addColumn({ column })"
		/>
		<div v-if="newColumnType == 'Expression'" class="text-center text-gray-500">
			Coming Soon...
		</div>
	</div>
</template>

<script setup>
import MetricPicker from '@/components/Query/MetricPicker.vue'
import DimensionPicker from '@/components/Query/DimensionPicker.vue'

import { inject, ref } from 'vue'

defineEmits(['close'])
const query = inject('query')
const newColumnType = ref('Metric')
</script>
