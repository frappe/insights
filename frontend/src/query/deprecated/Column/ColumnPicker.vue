<template>
	<div class="flex w-full flex-shrink-0 items-center bg-white pb-2">
		<Button icon="chevron-left" class="mr-2" @click="$emit('close')"> </Button>
		<div class="text-sm uppercase tracking-wide text-gray-700">Add Column</div>
	</div>
	<div class="flex flex-1 flex-col space-y-3 overflow-y-scroll">
		<div
			class="flex h-9 flex-shrink-0 cursor-pointer items-center space-x-2 rounded bg-gray-100 p-1 text-sm"
		>
			<div
				v-for="tab in ['Simple', 'Expression']"
				class="flex h-full flex-1 items-center justify-center rounded"
				:class="{
					' bg-white font-normal shadow': newColumnType == tab,
				}"
				@click.prevent.stop="newColumnType = tab"
			>
				{{ tab }}
			</div>
		</div>
		<SimpleColumnPicker v-if="newColumnType == 'Simple'" @close="$emit('close')" />
		<ColumnExpressionPicker v-if="newColumnType == 'Expression'" @close="$emit('close')" />
	</div>
</template>

<script setup>
import SimpleColumnPicker from './SimpleColumnPicker.vue'
import ColumnExpressionPicker from './ColumnExpressionPicker.vue'

import { ref } from 'vue'
defineEmits(['close'])
const newColumnType = ref('Simple')
</script>
