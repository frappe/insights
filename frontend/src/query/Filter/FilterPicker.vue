<template>
	<div class="mb-3 flex h-7 items-center">
		<Button icon="chevron-left" class="mr-2" @click="$emit('close')"> </Button>
		<div class="text-sm tracking-wide text-gray-600">{{ editing ? 'EDIT' : 'ADD' }} FILTER</div>
	</div>
	<div class="flex h-[calc(100%-2.75rem)] flex-col space-y-3">
		<div
			class="flex h-9 flex-shrink-0 items-center space-x-2 rounded-md bg-gray-100 p-1 text-sm"
		>
			<div
				class="flex h-full flex-1 items-center justify-center rounded font-light"
				:class="{
					'bg-white font-normal shadow': filterType == 'simple',
				}"
				@click.prevent.stop="filterType = 'simple'"
			>
				Simple
			</div>
			<div
				class="flex h-full flex-1 items-center justify-center rounded"
				:class="{
					' bg-white font-normal shadow': filterType == 'expression',
				}"
				@click.prevent.stop="filterType = 'expression'"
			>
				Expression
			</div>
		</div>
		<SimpleFilterPicker
			v-if="filterType == 'simple'"
			:filter="props.filter"
			@filter-select="(args) => $emit('filter-select', args)"
		/>
		<FilterExpressionPicker
			v-if="filterType == 'expression'"
			:filter="props.filter"
			@filter-select="(args) => $emit('filter-select', args)"
		/>
	</div>
</template>

<script setup>
import SimpleFilterPicker from '@/query/Filter/SimpleFilterPicker.vue'
import FilterExpressionPicker from '@/query/Filter/FilterExpressionPicker.vue'

import { ref } from 'vue'

const props = defineProps(['filter'])
defineEmits(['filter-select', 'close'])
const editing = ref(Boolean(props.filter))
const filterType = ref('simple')
</script>
