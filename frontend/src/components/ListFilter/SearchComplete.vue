<template>
	<Autocomplete
		placeholder="Select an option"
		:options="options"
		:modelValue="selection"
		@update:query="(q) => onUpdateQuery(q)"
		@update:modelValue="(v) => (selection = v.value)"
	/>
</template>

<script setup>
import { Autocomplete, createListResource } from 'frappe-ui'
import { computed, watch } from 'vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	value: {
		type: String,
		required: false,
		default: '',
	},
	doctype: {
		type: String,
		required: true,
	},
	searchField: {
		type: String,
		required: false,
		default: 'name',
	},
	labelField: {
		type: String,
		required: false,
		default: 'name',
	},
	valueField: {
		type: String,
		required: false,
		default: 'name',
	},
	pageLength: {
		type: Number,
		required: false,
		default: 10,
	},
})

watch(
	() => props.doctype,
	(value) => {
		r.doctype = value
		r.reload()
	}
)

const selection = computed({
	get: () => props.value,
	set: (value) => emit('update:modelValue', value),
})
const r = createListResource({
	doctype: props.doctype,
	pageLength: props.pageLength,
	cache: ['link_doctype', props.doctype],
	auto: true,
	fields: [props.labelField, props.searchField, props.valueField],
	onSuccess: () => {},
})
const options = computed(() => {
	const allOptions =
		r.data?.map((result) => ({
			label: result[props.labelField],
			value: result[props.valueField],
		})) || []

	if (selection.value && !allOptions.find((o) => o.value === selection.value)) {
		allOptions.push({
			label: selection.value,
			value: selection.value,
		})
	}
	return allOptions
})

function onUpdateQuery(query) {
	r.update({
		filters: {
			[props.searchField]: ['like', `%${query}%`],
		},
	})

	r.reload()
}
</script>
