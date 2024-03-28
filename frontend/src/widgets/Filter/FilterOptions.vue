<script setup>
import { getQueriesColumn, getQueryColumns } from '@/dashboard/useDashboards'
import FilterValueSelector from '@/query/visual/FilterValueSelector.vue'
import { getOperatorOptions } from '@/utils'
import { computed, inject, reactive, ref, watch } from 'vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	modelValue: { type: Object, required: true },
})

const options = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})
if (!options.value.links) options.value.links = {}
if (!options.value.column) options.value.column = {}
function updateOptions(key, value) {
	options.value = { ...options.value, [key]: value }
}

const dashboard = inject('dashboard')
const charts = dashboard.doc.items.filter((item) => dashboard.isChart(item))
const queries = charts.map((i) => i.options.query)

const filterColumnOptions = ref([])
getQueriesColumn(queries).then((columns) => {
	filterColumnOptions.value = columns.map((column) => {
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

async function handleCheck(checked, chartItem) {
	const links = options.value.links
	if (checked) {
		links[chartItem.item_id] = {}
		if (!chartColumnOptions[chartItem.options.query]) {
			// fetch and set the column options for this chart
			await setColumnOptions(chartItem)
		}
		// if there is a column named the same as the filter column, select it
		const column = chartColumnOptions[chartItem.options.query]?.find(
			(c) =>
				c.column?.toLowerCase() === options.value.column.column?.toLowerCase() &&
				c.table?.toLowerCase() === options.value.column.table?.toLowerCase()
		)
		if (column) {
			links[chartItem.item_id] = column
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

const operatorOptions = computed(() => {
	const _options = getOperatorOptions(options.value.column?.type)
	return _options
		.filter((option) => option.value !== 'is')
		.concat([
			{ label: 'is set', value: 'is_set' },
			{ label: 'is not set', value: 'is_not_set' },
		])
})
// prettier-ignore
watch(() => options.value.defaultOperator?.value, (newVal, oldVal) => {
	if (newVal !== oldVal) {
		options.value.defaultValue = {}
	}
})

// watch(() => options.value.column?.column, () => {
// 	// select all the charts that have this column
// 	const links = options.value.links
// 	const column = options.value.column
// 	if (!column?.column) return
// 	debugger
// 	charts.forEach((chart) => {
// 		if (chart.options.query && chartColumnOptions[chart.options.query]) {
// 			const chartColumn = chartColumnOptions[chart.options.query].find(
// 				(c) => c.column === column.column
// 			)
// 			if (chartColumn) {
// 				links[chart.item_id] = chartColumn
// 			}
// 		}
// 	})
// 	updateOptions('links', links)
// })
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
				:options="filterColumnOptions"
				placeholder="Select a column"
			></Autocomplete>
		</div>

		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Default Operator</span>
			<Autocomplete
				v-model="options.defaultOperator"
				placeholder="Default Operator"
				:options="operatorOptions"
			></Autocomplete>
		</div>

		<div v-if="options.column?.value">
			<FilterValueSelector
				label="Default Value"
				:column="options.column"
				:operator="options.defaultOperator"
				:modelValue="options.defaultValue"
				:data-source="options.column?.data_source"
				@update:modelValue="options.defaultValue = $event"
			/>
		</div>

		<div v-if="options.column?.column">
			<div class="mb-2 space-y-1">
				<span class="block text-sm leading-4 text-gray-700">Links</span>
				<span class="block text-xs leading-4 text-gray-600">
					Select charts to link to this filter. The filter will be applied to the selected
					column in the linked charts.
				</span>
			</div>
			<div class="max-h-[20rem] space-y-2 overflow-y-auto">
				<div
					class="flex h-8 w-full items-center"
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
						class="mx-2 flex-1 truncate text-base font-medium"
						:class="[
							options.links[chartItem.item_id]
								? 'text-gray-900'
								: 'font-normal text-gray-600',
						]"
					>
						{{ chartItem.options.title }}
					</span>
					<Autocomplete
						v-if="options.links[chartItem.item_id] && chartItem.options.query"
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
