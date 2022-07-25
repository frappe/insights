<script setup>
import { computed, inject, watch, ref, onMounted } from 'vue'
const props = defineProps({
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

// resize the font if width or height is changed
const valueElem = ref(null)
onMounted(() => {
	if (layout) {
		watch(
			layout,
			() => {
				// set font size to fit
				const fontSize = layout.width / 5
				valueElem.value.style.fontSize = fontSize + 'px'
			},
			{ immediate: true }
		)
	}
})
</script>

<template>
	<div class="flex h-full w-full items-center justify-center">
		<div ref="valueElem" class="text-8xl">{{ formattedValue }}</div>
	</div>
</template>
