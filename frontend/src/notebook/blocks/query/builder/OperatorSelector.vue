<script setup>
import { getOperatorOptions } from '@/utils'
import { computed } from 'vue'
import InputWithPopover from './InputWithPopover.vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	column_type: String,
	modelValue: Object,
})
const operator = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})
const operators = computed(() => {
	const options = getOperatorOptions(props.column_type)
	return options
		.filter((option) => option.value !== 'is')
		.concat([
			{ label: 'is set', value: 'is_set' },
			{ label: 'is not set', value: 'is_not_set' },
		])
})
</script>

<template>
	<InputWithPopover
		v-model="operator"
		:items="operators"
		placeholder="Operator"
		class="min-w-0"
		:class="$attrs.class"
		:disableFilter="true"
	></InputWithPopover>
</template>
