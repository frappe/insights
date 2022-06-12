<template>
	<div class="flex flex-col space-y-3">
		<div class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Column</div>
			<Autocomplete
				v-model="dimension.column"
				:options="columnOptions"
				placeholder="Select a column..."
				@selectOption="onColumnSelect"
			/>
		</div>
		<div v-if="showFormatOptions" class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Format</div>
			<Autocomplete
				v-model="dimension.format"
				:options="formatOptions"
				placeholder="Select a format..."
				@selectOption="onFormatSelect"
			/>
		</div>
		<div v-if="dimension.label" class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Label</div>
			<Input
				type="text"
				v-model="dimension.label"
				class="h-8 placeholder:text-sm"
				placeholder="Enter a label..."
			/>
		</div>
		<div class="flex justify-end space-x-2">
			<Button
				v-if="column.name"
				class="text-red-500"
				appearance="white"
				@click="
					() => {
						query.removeColumn({ column })
						$emit('close')
					}
				"
			>
				Remove
			</Button>
			<Button @click="addDimension" appearance="primary" :disabled="addDisabled">
				{{ column.name ? 'Edit' : 'Add ' }}
			</Button>
		</div>
	</div>
</template>

<script setup>
import { isEmptyObj } from '@/utils/utils.js'
import Autocomplete from '@/components/Autocomplete.vue'

import { computed, inject, onMounted, reactive } from 'vue'

const query = inject('query')

const emit = defineEmits(['column-select', 'close'])
const props = defineProps({
	column: {
		type: Object,
		default: {},
	},
})

const dimension = reactive({
	column: props.column,
	label: props.column.label,
	format: props.column.format
		? {
				label: props.column.format,
				value: props.column.format,
		  }
		: {},
})

onMounted(() => query.fetchColumns())

const addDisabled = computed(() => {
	return isEmptyObj(dimension.column) || !dimension.label
})

const columnOptions = computed(() => {
	return query.fetchColumnsData.value?.map((c) => {
		return {
			...c,
			value: c.column,
			secondary_label: c.table_label,
		}
	})
})

const showFormatOptions = computed(() => {
	return (
		!isEmptyObj(dimension.column) &&
		['Datetime', 'Timestamp', 'Date'].includes(dimension.column.type)
	)
})

const formatOptions = computed(() => {
	if (!showFormatOptions.value) return []

	let formatOptions = []

	if (['Datetime', 'Timestamp'].includes(dimension.column.type)) {
		formatOptions = [
			'Minute',
			'Hour',
			'Day',
			'Month',
			'Year',
			'Minute of Hour',
			'Hour of Day',
			'Day of Week',
			'Day of Month',
			'Day of Year',
			'Month of Year',
			'Quarter of Year',
		]
	}

	if (dimension.column.type == 'Date') {
		formatOptions = [
			'Day',
			'Month',
			'Year',
			'Day of Week',
			'Day of Month',
			'Day of Year',
			'Month of Year',
			'Quarter of Year',
		]
	}

	return formatOptions.map((f) => {
		return {
			label: f,
			value: f,
		}
	})
})

function onColumnSelect(option) {
	dimension.column = option ? option : {}
	dimension.label =
		!dimension.label && dimension.column.label ? dimension.column.label : dimension.label
}
function onFormatSelect(option) {
	dimension.format = option ? option : {}
}
function addDimension() {
	if (isEmptyObj(dimension.column)) {
		return
	}

	dimension.column.label = dimension.label
	dimension.column.aggregation = 'Group By'
	dimension.column.format = dimension.format.value
	emit('column-select', dimension.column)
}
</script>
