<script setup>
import { computed, inject, reactive, watch } from 'vue'

const props = defineProps({ modelValue: Object })
const emit = defineEmits(['update:modelValue'])

const form = reactive({
	item_type: 'Filter',
	filter_label: '',
	filter_column: {},
	filter_links: {},
})

if (props.modelValue) {
	form.filter_label = props.modelValue.filter_label || ''
	form.filter_column = props.modelValue.filter_column || {}
	form.filter_links = props.modelValue.filter_links || {}
}

watch(
	() => form,
	(value) => emit('update:modelValue', value),
	{ deep: true }
)

const dashboard = inject('dashboard')
const chartItems = computed(() => {
	return dashboard.items.filter((item) => {
		return item.item_type === 'Chart'
	})
})

function handleCheck(checked, chartItem) {
	const links = form.filter_links || {}
	if (checked) {
		links[chartItem.chart] = {}
		if (!chartColumnOptions[chartItem.query]) {
			setColumnOptions(chartItem)
		}
	} else {
		delete links[chartItem.chart]
	}
	form.filter_links = links
}

const chartColumnOptions = reactive({})
function setColumnOptions(chartItem) {
	if (!form.filter_column?.column) return
	const request = dashboard.fetchAllColumns(chartItem.query)
	chartColumnOptions[chartItem.chart] = computed(() => {
		return request.data
			?.filter((c) => {
				return (
					c.type === form.filter_column.type &&
					c.table === form.filter_column.table &&
					c.column === form.filter_column.column &&
					c.data_source === form.filter_column.data_source
				)
			})
			.map((column) => {
				return {
					label: column.label,
					column: column.column,
					table: column.table,
					type: column.type,
					table_label: column.table_label,
					data_source: column.data_source,
					value: `${column.table}.${column.column}`,
				}
			})
	})
}

const columnOptionsRequest = dashboard.getFilterColumns()
const filterColumnOptions = computed(() => {
	return columnOptionsRequest.data?.map((column) => {
		return {
			label: column.label,
			column: column.column,
			type: column.type,
			table: column.table,
			data_source: column.data_source,
			description: `${column.type} - ${column.table_label}`,
		}
	})
})
</script>

<template>
	<div class="space-y-3">
		<Input
			type="text"
			label="Label"
			v-model="form.filter_label"
			placeholder="Enter filter label"
		></Input>
		<div class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Filter by Column</div>
			<Autocomplete
				placeholder="Select a column"
				:options="filterColumnOptions"
				v-model="form.filter_column"
			></Autocomplete>
		</div>

		<div v-if="form.filter_column?.column">
			<div class="mb-2 block text-sm leading-4 text-gray-700">Links</div>
			<div class="max-h-[15rem] space-y-2 overflow-y-auto">
				<div
					class="flex h-8 w-full items-center text-gray-600"
					v-for="chartItem in chartItems"
					:key="chartItem.chart"
				>
					<div
						class="flex flex-1 items-center text-ellipsis whitespace-nowrap text-base font-medium"
					>
						<Input
							type="checkbox"
							:label="chartItem.chart_title"
							class="focus:ring-0"
							@change="handleCheck($event, chartItem)"
							:value="form.filter_links[chartItem.chart]"
						></Input>
					</div>
					<Autocomplete
						v-if="form.filter_links[chartItem.chart]"
						placeholder="Select Column"
						:options="chartColumnOptions[chartItem.chart]"
						v-model="form.filter_links[chartItem.chart]"
						:empty-text="`No ${form.filter_column.type.toLowerCase()} columns found`"
					></Autocomplete>
				</div>
			</div>
		</div>
	</div>
</template>
