<template>
	<div class="flex h-8 w-full cursor-pointer select-none items-center rounded bg-gray-100 p-1">
		<div
			v-for="tab in tabs"
			class="flex h-full flex-1 items-center justify-center px-4 text-sm transition-all"
			:class="{
				'rounded bg-white shadow': tab.active || (modelValue && modelValue === tab.value),
				'cursor-not-allowed': tab.disabled,
			}"
			@click="handleClick(tab)"
		>
			{{ tab.label }}
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	modelValue: { type: Object, required: false },
	tabs: { type: Array, required: true },
})
const emit = defineEmits(['switch', 'update:modelValue'])
function handleClick(tab) {
	if (tab.disabled) return
	emit('switch', tab)
	emit('update:modelValue', tab.value)
}
</script>
