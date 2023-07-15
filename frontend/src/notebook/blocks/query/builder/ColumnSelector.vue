<script setup>
import UsePopover from '@/components/UsePopover.vue'
import { useDataSourceTable } from '@/datasource/useDataSource'
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
	const localColumns = props.localColumns.filter(filterFn)
	if (!tables.value?.length) return localColumns
	const tableColumns = tables.value
		.map((d) => d.doc?.columns)
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
	if (column.description == 'local') return column.alias
	return column.expression?.raw || `${column.table}.${column.column}`
}

const columnOptions = computed(() => {
	if (!columns.value?.length) return []
	return columns.value.map((c) => {
		return {
			label: c.label || c.alias,
			description: c.description || c.table,
			table_label: c.table_label,
			value: getColumnValue(c),
		}
	})
})

const columnOptionsGroupedByTable = computed(() => {
	if (!columnOptions.value?.length) return []
	const grouped = {}
	columnOptions.value.forEach((c) => {
		if (!grouped[c.table_label]) grouped[c.table_label] = []
		grouped[c.table_label].push(c)
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
		emit('update:modelValue', {
			...column,
			...option,
			alias: column.alias || props.modelValue.alias,
			order: column.order || props.modelValue.order,
			granularity: column.granularity || props.modelValue.granularity,
			aggregation: column.aggregation || props.modelValue.aggregation,
			format: column.format || props.modelValue.format,
			expression: column.expression || props.modelValue.expression,
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
			<span> {{ column?.label || 'Pick a column' }} </span>
		</div>
		<UsePopover ref="columnPopover" v-if="trigger" :targetElement="trigger">
			<div class="w-[12rem] rounded border bg-white text-base shadow transition-[width]">
				<div class="flex items-center rounded-t-md border-b bg-white px-2">
					<FeatherIcon name="search" class="h-4 w-4 text-gray-600" />
					<input
						v-model="columnSearchTerm"
						class="flex w-full items-center bg-white px-2 py-1.5 text-sm focus:outline-none"
						placeholder="Search column..."
					/>
				</div>
				<div class="max-h-48 overflow-y-auto text-sm">
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
							class="sticky top-0 flex items-center border-b bg-white px-2 py-1 text-gray-700"
						>
							<FeatherIcon name="table" class="mr-1 h-3.5 w-3.5" />
							<span class="flex-1 py-0.5 text-sm">
								{{ table }}
							</span>
						</div>
						<div v-for="col in filteredColumnOptionsGroupedByTable[table]">
							<div
								class="flex cursor-pointer items-center justify-between p-2 transition-all hover:bg-gray-100"
								:class="column?.value === col.value ? 'bg-gray-100' : ''"
								@click="handleColumnSelect(col)"
							>
								<span>{{ col.label }}</span>
							</div>
						</div>
					</div>
				</div>
			</div>
		</UsePopover>
	</div>
</template>
