<script setup>
import { FIELDTYPES } from '@/utils'
import { dateFormats } from '@/utils/format'
import { computed } from 'vue'

const props = defineProps({
	modelValue: { type: Object, required: true },
	column: { type: Object, required: true },
})

if (!props.modelValue.column_type) {
	props.modelValue.column_type = FIELDTYPES.NUMBER.includes(props.column?.type)
		? 'Number'
		: FIELDTYPES.DATE.includes(props.column?.type)
		? 'Date'
		: 'Text'
}

const emit = defineEmits(['update:modelValue'])
const options = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})

const columnTypeOptions = computed(() => {
	if (!props.column?.type) return []
	if (FIELDTYPES.NUMBER.includes(props.column?.type)) {
		return ['Number', 'Text', 'Link']
	}
	if (FIELDTYPES.TEXT.includes(props.column?.type)) {
		return ['Text', 'Link']
	}
	if (FIELDTYPES.DATE.includes(props.column?.type)) {
		return ['Text', 'Date']
	}
	return []
})
</script>

<template>
	<div class="flex flex-col gap-3">
		<FormControl
			label="Column Type"
			type="select"
			:options="columnTypeOptions"
			v-model="options.column_type"
		/>
		<FormControl
			v-if="options.column_type === 'Link'"
			type="text"
			label="Link URL"
			autocomplete="off"
			placeholder="eg. https://github.com/{{ value }}"
			description="Use {{ value }} to substitute the value of the column"
			v-model="options.link_url"
		/>
		<FormControl
			v-if="options.column_type === 'Number'"
			type="text"
			label="Prefix"
			autocomplete="off"
			v-model="options.prefix"
			placeholder="Enter a prefix..."
		/>
		<FormControl
			v-if="options.column_type === 'Number'"
			type="text"
			label="Suffix"
			autocomplete="off"
			v-model="options.suffix"
			placeholder="Enter a suffix..."
		/>
		<FormControl
			v-if="options.column_type === 'Number'"
			type="number"
			label="Decimals"
			autocomplete="off"
			v-model="options.decimals"
			placeholder="Enter a number..."
		/>
		<Checkbox
			v-if="options.column_type === 'Number'"
			v-model="options.show_inline_bar_chart"
			label="Show Inline Bar Chart"
		/>
		<FormControl
			v-if="options.column_type === 'Date'"
			type="select"
			label="Date Format"
			autocomplete="off"
			v-model="options.date_format"
			placeholder="Select a date format..."
			:options="dateFormats"
		/>
	</div>
</template>
