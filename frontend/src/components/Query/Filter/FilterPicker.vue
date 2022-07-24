<template>
	<div class="mb-4 flex h-7 items-center">
		<Button icon="chevron-left" class="mr-2" @click="$emit('close')"> </Button>
		<div class="text-lg font-medium">{{ editing ? 'Edit' : 'Add' }} a Filter</div>
	</div>
	<div class="flex flex-col space-y-3">
		<div class="flex h-9 items-center space-x-2 rounded-md border bg-gray-50 p-0.5 text-sm">
			<div
				class="flex h-full flex-1 items-center justify-center rounded-md font-light"
				:class="{
					'border bg-white font-normal shadow-sm': filterType == 'simple',
				}"
				@click.prevent.stop="filterType = 'simple'"
			>
				Simple
			</div>
			<div
				class="flex h-full flex-1 items-center justify-center rounded-md"
				:class="{
					'border bg-white font-normal shadow-sm': filterType == 'expression',
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
import SimpleFilterPicker from '@/components/Query/Filter/SimpleFilterPicker.vue'
import FilterExpressionPicker from '@/components/Query/Filter/FilterExpressionPicker.vue'

import { ref } from 'vue'

const props = defineProps(['filter'])
defineEmits(['filter-select', 'close'])
const editing = ref(Boolean(props.filter))
const filterType = ref('simple')
</script>
