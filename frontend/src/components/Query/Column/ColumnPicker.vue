<template>
	<div class="sticky top-0 z-10 flex items-center bg-white pb-3 pt-1">
		<Button icon="chevron-left" class="mr-2" @click="$emit('close')"> </Button>
		<div class="text-sm uppercase tracking-wide text-gray-600">Add Column</div>
	</div>
	<div class="flex flex-col space-y-3">
		<div
			class="flex h-9 cursor-pointer items-center space-x-2 rounded-md bg-gray-100 p-1 text-sm"
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
import SimpleColumnPicker from '@/components/Query/Column/SimpleColumnPicker.vue'
import ColumnExpressionPicker from '@/components/Query/Column/ColumnExpressionPicker.vue'

import { ref } from 'vue'
defineEmits(['close'])
const newColumnType = ref('Simple')
</script>
