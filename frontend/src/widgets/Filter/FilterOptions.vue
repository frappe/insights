<script setup>
import { getQueriesColumn, getQueryColumns } from '@/dashboard/useDashboards'
import { computed, inject, reactive, ref } from 'vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	modelValue: { type: Object, required: true },
})

const options = computed({
	get() {
		return props.modelValue
	},
	set(value) {
		emit('update:modelValue', value)
	},
})
if (!options.value.links) options.value.links = {}
if (!options.value.column) options.value.column = {}
function updateOptions(key, value) {
	options.value = { ...options.value, [key]: value }
}

const dashboard = inject('dashboard')
const charts = dashboard.doc.items.filter((item) => {
	return item.item_type !== 'Filter' && item.item_type !== 'Text' && item.options.query
})
const queries = charts.map((i) => i.options.query)

const columnOptions = ref([])
getQueriesColumn(queries).then((columns) => {
	columnOptions.value = columns.map((column) => {
		return {
			label: column.label,
			column: column.column,
			type: column.type,
			table: column.table,
			data_source: column.data_source,
			description: `${column.type} - ${column.table_label}`,
			value: `${column.table}.${column.column}`,
		}
	})
})

charts.forEach((chart) => {
	if (options.value.links[chart.item_id]) {
		setColumnOptions(chart)
	}
})

function handleCheck(checked, chartItem) {
	const links = options.value.links
	if (checked) {
		links[chartItem.item_id] = {}
		if (!chartColumnOptions[chartItem.options.query]) {
			setColumnOptions(chartItem)
		}
	} else {
		delete links[chartItem.item_id]
	}
	updateOptions('links', links)
}

const chartColumnOptions = reactive({})
async function setColumnOptions(chartItem) {
	const filter_column = options.value.column
	if (!filter_column?.column) return
	const columns = await getQueryColumns(chartItem.options.query)
	chartColumnOptions[chartItem.options.query] = columns.map((column) => {
		return {
			label: column.label,
			column: column.column,
			table: column.table,
			type: column.type,
			table_label: column.table_label,
			data_source: column.data_source,
			description: `${column.type} - ${column.table_label}`,
			value: `${column.table}.${column.column}`,
		}
	})
}
</script>

<template>
	<div class="space-y-4">
		<Input
			type="text"
			label="Label"
			v-model="options.label"
			placeholder="Enter filter label"
		></Input>

		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Column</span>
			<Autocomplete
				v-model="options.column"
				:options="columnOptions"
				placeholder="Select a column"
			></Autocomplete>
		</div>

		<div v-if="options.column?.column">
			<span class="mb-2 block text-sm leading-4 text-gray-700">Links</span>
			<div class="max-h-[20rem] space-y-2">
				<div
					class="flex h-8 w-full items-center text-gray-600"
					v-for="chartItem in charts"
					:key="chartItem.item_id"
				>
					<Input
						type="checkbox"
						class="flex-shrink-0 focus:ring-0"
						@change="handleCheck($event, chartItem)"
						:value="options.links[chartItem.item_id]"
					></Input>
					<span
						class="mx-2 flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-base font-medium"
						:class="[
							options.links[chartItem.item_id]
								? 'text-gray-900'
								: 'font-normal text-gray-600',
						]"
					>
						{{ chartItem.options.title }}
					</span>
					<Autocomplete
						v-if="options.links[chartItem.item_id]"
						class="w-28 flex-shrink-0"
						placeholder="Select Column"
						:options="chartColumnOptions[chartItem.options.query]"
						v-model="options.links[chartItem.item_id]"
						empty-text="No matching columns found"
					></Autocomplete>
				</div>
			</div>
		</div>
	</div>
</template>
