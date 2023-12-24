<template>
	<div
		class="flex h-7.5 w-full cursor-pointer select-none items-center rounded bg-gray-100 p-0.5"
	>
		<div
			v-for="tab in tabs"
			class="flex h-full flex-1 items-center justify-center truncate px-4 transition-all"
			:class="{
				'rounded bg-white shadow': tab.active || modelValue === tab.value,
				'cursor-not-allowed': tab.disabled,
			}"
			@click="handleClick(tab)"
		>
			{{ tab.label }}
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue'

const emit = defineEmits(['switch', 'update:modelValue'])
const props = defineProps({
	modelValue: { required: false },
	tabs: { type: Array, required: true },
})

const tabs = computed(() => {
	if (typeof props.tabs?.[0] == 'string') {
		return props.tabs.map((label) => ({ label, value: label }))
	}
	return props.tabs
})
function handleClick(tab) {
	if (tab.disabled) return
	emit('switch', tab)
	emit('update:modelValue', tab.value)
}
</script>
