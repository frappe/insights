<script setup>
import { computed } from 'vue'
import { getOperatorOptions } from '@/utils/query/columns'

const props = defineProps({ modelValue: Object })
const emits = defineEmits(['update:modelValue'])

const filter = computed({
	get: () => props.modelValue,
	set: (value) => emits('update:modelValue', value),
})

const filterTypeOptions = ['String', 'Integer', 'Decimal', 'Date', 'Datetime']
const operatorOptions = computed(() => getOperatorOptions(filter.value.filter_type))
</script>

<template>
	<div class="space-y-3">
		<Input type="text" label="Label" v-model="filter.filter_label"></Input>
		<Input
			type="select"
			label="Type"
			v-model="filter.filter_type"
			:options="filterTypeOptions"
		></Input>
		<Input
			type="select"
			label="Operator"
			:options="operatorOptions"
			v-model="filter.filter_operator"
		></Input>
	</div>
</template>
