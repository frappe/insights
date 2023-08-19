<script setup>
import UsePopover from '@/components/UsePopover.vue'
import useDataSourceTable from '@/datasource/useDataSourceTable'
import { computed, ref, watch } from 'vue'
const props = defineProps({
	data_source: String,
	tables: Array,
	modelValue: Object,
	columnFilter: Function,
	value: { type: Object, default: undefined },
	placeholder: { type: String, default: 'Column' },
	localColumns: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue'])

const tables = ref([])
watch(
	() => props.tables,
	async () => {
		if (!props.tables?.length) return []
		const tablePromises = []
		props.tables.forEach((table) => {
			if (!table.table) return Promise.resolve()
			tablePromises.push(
				useDataSourceTable({
					data_source: props.data_source,
					table: table.table,
				})
			)
		})
		tables.value = await Promise.all(tablePromises)
	},
	{ immediate: true }
)

const columns = computed(() => {
	const localColumns = props.localColumns.filter(filterFn).map((c) => ({ ...c, isLocal: true }))
	if (!tables.value?.length) return localColumns
	const tableColumns = tables.value
		.map((table) => table.columns)
		.flat()
		.filter(filterFn)
	return localColumns.concat(tableColumns)
})
function filterFn(col, currIndex, self) {
	if (!col) return false
	const otherIndex = self.findIndex((c) => getColumnValue(c) === getColumnValue(col))
	return otherIndex === currIndex && (!props.columnFilter || props.columnFilter(col))
}
function getColumnValue(column) {
	if (!column) return
	if (column.expression?.raw) return column.expression.raw

	let value = `${column.table}.${column.column}`
	if (column.granularity) value = `${column.granularity}(${value})`
	if (column.aggregation) value = `${column.aggregation}(${value})`
	return value
}

const columnOptions = computed(() => {
	if (!columns.value?.length) return []
	return columns.value.map((c) => {
		return {
			label: c.label || c.alias,
			group: c.isLocal ? 'Local' : c.table_label,
			description: c.column,
			value: getColumnValue(c),
		}
	})
})

const columnOptionsGroupedByTable = computed(() => {
	if (!columnOptions.value?.length) return []
	const grouped = {}
	columnOptions.value.forEach((c) => {
		if (c.description == 'local') c.group = 'Local'
		if (!grouped[c.group]) grouped[c.group] = []
		grouped[c.group].push(c)
	})
	return grouped
})

const valuePropPassed = computed(() => props.value !== undefined)
const column = computed({
	get: () =>
		// hacky: because unless the exact matching object is passed
		// the combobox doesn't select the value
		// so, we find the matching object from the columnOptions using the value
		// this way, as long actual value is passed, it will select the correct option
		findOptionByValue(
			columns.value,
			valuePropPassed.value ? getColumnValue(props.value) : getColumnValue(props.modelValue)
		),
	set: (option) => {
		const column = findOptionByValue(columns.value, option.value)
		const passedValue = valuePropPassed.value ? props.value : props.modelValue
		emit('update:modelValue', {
			...column,
			...option,
			alias: column.alias || passedValue.alias,
			order: column.order || passedValue.order,
			granularity: column.granularity || passedValue.granularity,
			aggregation: column.aggregation || passedValue.aggregation,
			format: column.format || passedValue.format,
			expression: column.expression || passedValue.expression,
			meta: column.meta || passedValue.meta,
		})
	},
})

function findOptionByValue(columns, value) {
	return columns.find((c) => value == getColumnValue(c))
}

const filteredColumnOptionsGroupedByTable = computed(() => {
	// returns grouped options with only the options that match the search term
	// matches table, label, value
	if (!columnOptionsGroupedByTable.value) return []
	const filtered = {}
	Object.keys(columnOptionsGroupedByTable.value).forEach((table) => {
		const options = columnOptionsGroupedByTable.value[table]
		const filteredOptions = options.filter((o) => {
			return (
				o.label.toLowerCase().includes(columnSearchTerm.value.toLowerCase()) ||
				o.value.toLowerCase().includes(columnSearchTerm.value.toLowerCase()) ||
				o.description.toLowerCase().includes(columnSearchTerm.value.toLowerCase())
			)
		})
		if (filteredOptions.length) filtered[table] = filteredOptions
	})
	return filtered
})

const trigger = ref(null)
const columnSearchTerm = ref('')
const columnPopover = ref(null)
function handleColumnSelect(col) {
	column.value = col
	columnSearchTerm.value = ''
	columnPopover.value?.close()
}
</script>

<template>
	<div>
		<div
			ref="trigger"
			class="flex h-7 w-full cursor-pointer items-center overflow-hidden text-ellipsis !whitespace-nowrap px-2.5 leading-7 outline-none ring-0 transition-all focus:outline-none"
			:class="column?.label ? '' : 'text-gray-500'"
		>
			<span> {{ column?.label || 'Column' }} </span>
		</div>
		<UsePopover ref="columnPopover" v-if="trigger" :targetElement="trigger">
			<div class="min-w-[12rem] rounded bg-white p-1.5 text-base shadow transition-all">
				<Input
					iconLeft="search"
					:value="columnSearchTerm"
					@input="columnSearchTerm = $event"
					placeholder="Find column"
				/>
				<div class="mt-1 max-h-48 overflow-y-auto text-sm">
					<p
						v-if="
							columnOptions?.length === 0 ||
							filteredColumnOptionsGroupedByTable?.length === 0
						"
						class="p-2 text-center text-gray-600"
					>
						No columns found
					</p>
					<div v-else v-for="table in Object.keys(filteredColumnOptionsGroupedByTable)">
						<div
							class="sticky top-0 flex items-center bg-white px-2 py-1 text-gray-700"
						>
							<FeatherIcon name="table" class="mr-1 h-3.5 w-3.5" />
							<span class="flex-1 py-0.5 text-sm">
								{{ table }}
							</span>
						</div>
						<div v-for="col in filteredColumnOptionsGroupedByTable[table]">
							<div
								class="flex cursor-pointer items-center justify-between space-x-8 rounded p-2 transition-all hover:bg-gray-100"
								:class="column?.value === col.value ? 'bg-gray-100' : ''"
								@click="handleColumnSelect(col)"
							>
								<span>{{ col.label }}</span>
								<span class="text-xs text-gray-500">{{ col.description }}</span>
							</div>
						</div>
					</div>
				</div>
			</div>
		</UsePopover>
	</div>
</template>
