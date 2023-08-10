<script setup>
import { computed } from 'vue'

const emit = defineEmits(['update:modelValue', 'remove'])
const props = defineProps({
	modelValue: { type: Object, required: true },
	options: { type: Array, required: true },
})
const series = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})
</script>

<template>
	<div class="-m-1 flex flex-1 space-x-2 overflow-hidden p-1">
		<div class="-m-1 flex-1 overflow-hidden p-1">
			<Autocomplete
				:modelValue="series.column"
				:options="options"
				placeholder="Select a column"
				@update:modelValue="series.column = $event.value"
			/>
		</div>
		<div class="flex-shrink-0">
			<Button icon="x" variant="subtle" @click="$emit('remove')" />
		</div>
	</div>
</template>
