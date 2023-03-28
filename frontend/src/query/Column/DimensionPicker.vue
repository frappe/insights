<template>
	<div class="flex flex-col space-y-3">
		<div class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Column</div>
			<Autocomplete
				v-model="dimension.column"
				:options="columnOptions"
				placeholder="Select a column..."
				@change="onColumnSelect"
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
		<div v-if="showDateFormatOptions" class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Date Format</div>
			<Autocomplete
				v-model="dimension.dateFormat"
				:options="dateFormats"
				placeholder="Select a date format..."
				@change="selectDateFormat"
			/>
		</div>
		<div class="flex justify-end space-x-2">
			<Button
				v-if="row_name"
				class="text-red-500"
				appearance="white"
				@click="removeDimension"
			>
				Remove
			</Button>
			<Button @click="addDimension" appearance="primary" :disabled="addDisabled">
				{{ row_name ? 'Update' : 'Add ' }}
			</Button>
		</div>
	</div>
</template>

<script setup>
import { isEmptyObj } from '@/utils'
import Autocomplete from '@/components/Controls/Autocomplete.vue'

import { computed, inject, reactive, ref } from 'vue'
import { dateFormats } from '@/utils/format'

const query = inject('query')

const emit = defineEmits(['column-select', 'close'])
const props = defineProps({
	column: {
		type: Object,
		default: {},
	},
})

const dimension = reactive({
	column: { ...props.column, value: props.column.column },
	label: props.column.label,
	dateFormat: ['Date', 'Datetime'].includes(props.column.type)
		? dateFormats.find((format) => format.value === props.column.format_option?.date_format)
		: {},
})
// for editing a dimension
const row_name = ref(props.column.name)
const showDateFormatOptions = computed(() => ['Date', 'Datetime'].includes(dimension.column.type))

const addDisabled = computed(() => {
	return isEmptyObj(dimension.column) || !dimension.label
})

const columnOptions = query.columns.options

function onColumnSelect(option) {
	dimension.column = option ? option : {}
	dimension.label =
		!dimension.label && dimension.column.label ? dimension.column.label : dimension.label

	dimension.column.name = row_name.value
}
function addDimension() {
	if (isEmptyObj(dimension.column)) {
		return
	}

	emit('column-select', {
		...dimension.column,
		label: dimension.label,
		aggregation: 'Group By',
		format_option: {
			date_format: dimension.dateFormat.value,
		},
	})
}
function removeDimension() {
	query.removeColumn.submit({ column: dimension.column })
	emit('close')
}

function selectDateFormat(option) {
	dimension.dateFormat = option
}
</script>
