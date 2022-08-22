<script setup>
import { computed, inject, watch, ref, onMounted } from 'vue'
const props = defineProps({
	title: {
		type: String,
		default: '',
	},
	value: {
		type: Number,
		required: true,
	},
})
const layout = inject('layout')
const formattedValue = computed(() => {
	if (props.value < 1000) {
		return props.value
	}
	if (props.value < 1000000) {
		return (props.value / 1000).toFixed(1) + 'k'
	}
	if (props.value < 1000000000) {
		return (props.value / 1000000).toFixed(1) + 'm'
	}
	return (props.value / 1000000000).toFixed(1) + 'b'
})
</script>

<template>
	<div class="flex h-full w-full flex-col items-center justify-center">
		<div class="text-base font-semibold text-gray-600">{{ props.title }}</div>
		<div class="text-[44px] leading-tight">{{ formattedValue }}</div>
	</div>
</template>
