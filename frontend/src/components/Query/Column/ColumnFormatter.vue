<template>
	<div v-if="!supportsFormatting" class="px-12 text-center text-sm font-light text-gray-600">
		<p class="mb-2">The app doesn't support formatting for this column type just yet</p>
		<a href="https://github.com/frappe/insights/issue/new" class="text-blue-400 underline">
			Do you want to raise a feature request?
		</a>
	</div>
	<div v-else class="flex flex-col space-y-3">
		<div v-if="showDateFormatOptions" class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Date Format</div>
			<Autocomplete
				v-model="format.dateFormat"
				:options="dateFormatOptions"
				placeholder="Select a date format..."
				@selectOption="(option) => (format.dateFormat = option)"
			/>
		</div>
		<div v-if="showNumberFormatOptions" class="space-y-3 text-sm text-gray-600">
			<div class="space-y-1">
				<div class="font-light">Prefix</div>
				<Input type="text" v-model="format.prefix" placeholder="Enter a prefix..." />
			</div>
			<div class="space-y-1">
				<div class="font-light">Suffix</div>
				<Input type="text" v-model="format.suffix" placeholder="Enter a suffix..." />
			</div>
		</div>
		<div class="flex justify-end space-x-2">
			<Button @click="clearFormattingOptions" appearance="white" :disabled="false">
				Clear
			</Button>
			<Button @click="saveFormattingOptions" appearance="primary" :disabled="false">
				Save
			</Button>
		</div>
	</div>
</template>

<script setup>
import Autocomplete from '@/components/Controls/Autocomplete.vue'

import { reactive, ref, unref } from 'vue'
import { safeJSONParse } from '@/utils'

const dateFormats = [
	{ label: 'January 12, 2020', value: 'Day' },
	{ label: 'January, 2020', value: 'Month' },
	{ label: 'Q1, 2020', value: 'Quarter' },
	{ label: '2020', value: 'Year' },
	{ label: 'Monday', value: 'Day of Week' },
	{ label: 'January', value: 'Month of Year' },
	{ label: 'Q1', value: 'Quarter of Year' },
]

const dateTimeFormats = [
	{ label: 'January 12, 2020 1:14 PM', value: 'Minute' },
	{ label: 'January 12, 2020 1:00 PM', value: 'Hour' },
	{ label: '1:00 PM', value: 'Hour of Day' },
	{ label: 'January 12, 2020', value: 'Day' },
	{ label: 'January, 2020', value: 'Month' },
	{ label: 'Q1, 2020', value: 'Quarter' },
	{ label: '2020', value: 'Year' },
	{ label: 'Monday', value: 'Day of Week' },
	{ label: 'January', value: 'Month of Year' },
	{ label: 'Q1', value: 'Quarter of Year' },
]

const emit = defineEmits(['save'])
const props = defineProps({
	column: {
		type: Object,
		default: {},
		required: true,
	},
})

const supportsFormatting = ref(
	['Int', 'Bigint', 'Float', 'Decimal', 'Double', 'Date', 'Datetime', 'Timestamp'].includes(
		props.column.type
	)
)
const columnFormat = safeJSONParse(unref(props.column.format_option)) || {}
const format = reactive({
	dateFormat:
		props.column.type == 'Date'
			? dateFormats.find((format) => format.value === columnFormat.date_format)
			: props.column.type == 'Datetime'
			? dateTimeFormats.find((format) => format.value === columnFormat.date_format)
			: {},
	prefix: columnFormat.prefix || '',
	suffix: columnFormat.suffix || '',
})

const showDateFormatOptions = ref(['Date', 'Datetime', 'Timestamp'].includes(props.column.type))
const dateFormatOptions = ref(
	props.column.type == 'Date'
		? dateFormats
		: props.column.type == 'Datetime'
		? dateTimeFormats
		: []
)

const showNumberFormatOptions = ref(
	['Int', 'Bigint', 'Float', 'Decimal', 'Double'].includes(props.column.type)
)
const saveFormattingOptions = () => {
	const updatedColumn = unref(props.column)
	if (showDateFormatOptions.value) {
		updatedColumn.format_option = {
			date_format: format.dateFormat.value,
		}
	}
	if (showNumberFormatOptions.value) {
		updatedColumn.format_option = {
			prefix: format.prefix,
			suffix: format.suffix,
		}
	}
	emit('save', updatedColumn)
}

const clearFormattingOptions = () => {
	const updatedColumn = unref(props.column)
	updatedColumn.format_option = {}
	emit('save', updatedColumn)
}
</script>
