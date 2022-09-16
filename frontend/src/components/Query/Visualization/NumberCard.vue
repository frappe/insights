<script setup>
import { computed } from 'vue'
const props = defineProps({
	title: {
		type: String,
		default: '',
	},
	value: {
		type: Number,
	},
})
const formattedValue = computed(() => {
	let value = props.value || 0
	// check if value has a decimal part
	if (value % 1 !== 0) {
		value = value.toFixed(1)
	}
	if (value < 1000) {
		return value
	}
	if (value < 1000000) {
		return (value / 1000).toFixed(1) + 'k'
	}
	if (value < 1000000000) {
		return (value / 1000000).toFixed(1) + 'm'
	}
	return (value / 1000000000).toFixed(1) + 'b'
})
</script>

<template>
	<div class="flex h-full min-h-[6rem] w-full min-w-40 flex-col items-center justify-center">
		<div class="text-base font-semibold text-gray-600">{{ props.title }}</div>
		<div class="text-[44px] leading-tight">{{ formattedValue }}</div>
	</div>
</template>
