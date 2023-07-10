<script setup>
import { useDataSourceTable } from '@/datasource/useDataSource'
import { FIELDTYPES, isDimensionColumn } from '@/utils'
import { dateFormats } from '@/utils/format'
import { computed, inject, provide } from 'vue'
import useQuery from '../useQuery'
import ColumnExpressionSelector from './ColumnExpressionSelector.vue'
import ColumnSelector from './ColumnSelector.vue'
import InputWithPopover from './InputWithPopover.vue'
import OperatorSelector from './OperatorSelector.vue'
import QueryBuilderRow from './QueryBuilderRow.vue'
import ResizeableInput from './ResizeableInput.vue'
import SourceAndTableSelector from './SourceAndTableSelector.vue'
import TableSelector from './TableSelector.vue'
import ValueSelector from './ValueSelector.vue'

const props = defineProps({ name: String })
const query = useQuery(props.name)
query.autosave = true
await query.reload()
provide('query', query)

const legacyQuery = inject('query')
legacyQuery.beforeExecute?.(async () => await query.save())

const state = computed({
	get: () => (typeof query.doc.json == 'string' ? JSON.parse(query.doc.json) : query.doc.json),
	set: (value) => (query.doc.json = value),
})

const selectedTables = computed(() => {
	const tables = [state.value.table]
	state.value.joins.forEach((join) => {
		join.right_table.value && tables.push(join.right_table)
	})
	return tables
})

const GET_EMPTY_JOIN = () => ({
	left_table: {},
	right_table: {},
	join_type: { label: 'Left', value: 'left' },
	left_column: {},
	right_column: {},
})
const GET_EMPTY_FILTER = () => ({
	column: {},
	operator: {},
	value: {},
})
const COLUMN = {
	table: '',
	column: '',
	label: '',
	type: '',
	alias: '',
	order: '',
	granularity: 'Month',
	aggregation: '',
	format: {},
	expression: {},
}
const GET_EMPTY_COLUMN = () => ({
	column: { ...COLUMN },
})

function addBlock(type) {
	if (type == 'Summarise') {
		if (!state.value.measures.length) state.value.measures = [{ ...GET_EMPTY_COLUMN() }]
		if (!state.value.dimensions.length) state.value.dimensions = [{ ...GET_EMPTY_COLUMN() }]
		return
	}
	const typeToEmptyValue = {
		Combine: { ...GET_EMPTY_JOIN() },
		Filter: { ...GET_EMPTY_FILTER() },
		Select: { ...GET_EMPTY_COLUMN() },
		Sort: { ...GET_EMPTY_COLUMN() },
		Calculate: { ...GET_EMPTY_COLUMN() },
		Limit: 10,
	}
	const typeToKey = {
		Combine: 'joins',
		Filter: 'filters',
		Select: 'columns',
		Sort: 'orders',
		Calculate: 'calculations',
		Limit: 'limit',
	}
	const block = typeToEmptyValue[type]
	const key = typeToKey[type]

	// if joining and only one table is selected, use that table as the left table
	if (type == 'Combine' && selectedTables.value.length == 1) {
		block.left_table = selectedTables.value[0]
	}

	if (Array.isArray(state.value[key])) {
		state.value[key].push(block)
	} else {
		state.value[key] = block
	}
}

const AGGREGATIONS = [
	{ label: 'Count of Records', value: 'count' },
	{ label: 'Sum of', value: 'sum' },
	{ label: 'Average of', value: 'avg' },
	{ label: 'Unique values of', value: 'distinct' },
	{ label: 'Unique count of', value: 'distinct_count' },
	{ label: 'Minimum of', value: 'min' },
	{ label: 'Maximum of', value: 'max' },
	{ label: 'Custom', value: 'custom' },
]
function setAggregation(aggregation, measure) {
	if (aggregation.value == 'count') {
		Object.assign(measure.column, {
			label: 'Count',
			column: 'count',
			table: 'count',
			value: 'count',
			type: 'Integer',
			aggregation: aggregation.value,
		})
	} else {
		Object.assign(measure.column, {
			...GET_EMPTY_COLUMN().column,
			aggregation: aggregation.value,
		})
	}
}

const dateFormatOptions = [{ label: 'None', value: '' }].concat(
	dateFormats.map((f) => ({ label: f.value, value: f.value }))
)
function findByValue(array, value, defaultValue = {}) {
	return array.find((item) => item.value == value) || defaultValue
}

const ORDER = [
	{ value: 'asc', label: 'Ascending' },
	{ value: 'desc', label: 'Descending' },
]

function isValidColumn(column) {
	const is_expression = column.expression && column.expression.raw && column.expression.ast
	const is_table_column = column.column && column.table
	const has_label = column.label || column.alias
	return (is_table_column || is_expression) && column.type && has_label
}

const selectedColumns = computed(() => {
	const columns = []
	const addIfValid = (column) => isValidColumn(column) && columns.push(column)
	state.value.columns.forEach((c) => addIfValid(c.column))
	state.value.calculations.forEach((c) => addIfValid(c.column))
	state.value.measures.forEach((c) => addIfValid(c.column))
	state.value.dimensions.forEach((c) => addIfValid(c.column))
	return columns.map((c) => ({ ...c, label: c.alias || c.label, description: 'local' }))
})

const COLUMN_TYPES = [
	{ label: 'String', value: 'String' },
	{ label: 'Integer', value: 'Integer' },
	{ label: 'Decimal', value: 'Decimal' },
	{ label: 'Text', value: 'Text' },
	{ label: 'Datetime', value: 'Datetime' },
	{ label: 'Date', value: 'Date' },
	{ label: 'Time', value: 'Time' },
]

async function autoSelectJoinColumns(join) {
	if (!join.left_table?.table || !join.right_table?.table) return
	if (join.left_column?.table || join.right_column?.table) return
	const left_table = await useDataSourceTable({
		data_source: query.doc.data_source,
		table: join.left_table.table,
	})
	const left_table_links = left_table.doc.table_links
	const left_right_link = left_table_links.find((l) => l.foreign_table == join.right_table.table)
	if (!left_right_link) return

	const left_column = left_right_link.primary_key
	const right_column = left_right_link.foreign_key
	join.left_column = {
		table: join.left_table.table,
		column: left_column,
		value: `${join.left_table.table}.${left_column}`,
	}
	join.right_column = {
		table: join.right_table.table,
		column: right_column,
		value: `${join.right_table.table}.${right_column}`,
	}
}
</script>

<template>
	<div class="flex flex-1 flex-col justify-between px-3 py-1 text-base">
		<div class="space-y-3 overflow-scroll scrollbar-hide" :key="query.doc.data_source">
			<QueryBuilderRow label="Start with" :onRemove="() => (state.table = {})">
				<SourceAndTableSelector
					class="flex rounded-lg border border-gray-300 text-gray-800"
					v-model="state.table"
					@update:model-value="query.doc.data_source = $event.data_source"
				/>
			</QueryBuilderRow>

			<!-- Joins -->
			<QueryBuilderRow
				v-if="state.joins.length"
				v-for="(join, index) in state.joins"
				:key="index"
				label="Combine"
				:onRemove="() => state.joins.splice(index, 1)"
			>
				<InputWithPopover
					class="flex rounded-lg border border-gray-300 text-gray-800"
					placeholder="Pick a table"
					v-model="join.left_table"
					:items="selectedTables"
				></InputWithPopover>
				<div class="flex h-8 flex-shrink-0 text-sm uppercase leading-8 text-gray-500">
					and
				</div>
				<TableSelector
					class="flex rounded-lg border border-gray-300 text-gray-800"
					:data_source="query.doc.data_source"
					v-model="join.right_table"
					@update:model-value="() => autoSelectJoinColumns(join)"
				/>
				<div class="flex h-8 flex-shrink-0 text-sm uppercase leading-8 text-gray-500">
					if
				</div>
				<Suspense>
					<ColumnSelector
						class="flex rounded-lg border border-gray-300 text-gray-800"
						:data_source="query.doc.data_source"
						:tables="[join.left_table]"
						v-model="join.left_column"
					/>
				</Suspense>
				<div class="flex h-8 flex-shrink-0 text-sm uppercase leading-8 text-gray-500">
					matches
				</div>
				<Suspense>
					<ColumnSelector
						class="flex rounded-lg border border-gray-300 text-gray-800"
						:data_source="query.doc.data_source"
						:tables="[join.right_table]"
						v-model="join.right_column"
					/>
				</Suspense>
			</QueryBuilderRow>

			<!-- Expressions -->
			<QueryBuilderRow
				v-if="state.calculations.length"
				v-for="(calc, index) in state.calculations"
				:key="index"
				label="Calculate"
				:onRemove="() => state.calculations.splice(index, 1)"
			>
				<div
					class="flex items-center divide-x divide-gray-300 overflow-hidden rounded-lg border border-gray-300 text-gray-800"
				>
					<ColumnExpressionSelector v-model="calc.column.expression" />
				</div>

				<div class="h-8 text-sm uppercase leading-8 text-gray-500">as</div>
				<div
					class="flex items-center divide-x divide-gray-300 overflow-hidden rounded-lg border border-gray-300 text-gray-800"
				>
					<ResizeableInput
						placeholder="Label"
						v-model="calc.column.alias"
						@update:modelValue="calc.column.label = $event"
					/>
					<InputWithPopover
						:items="COLUMN_TYPES"
						placeholder="Type"
						:value="findByValue(COLUMN_TYPES, calc.column.type)"
						@update:modelValue="(v) => (calc.column.type = v.value)"
					/>
				</div>
			</QueryBuilderRow>

			<!-- Filters -->
			<QueryBuilderRow
				v-if="state.filters.length"
				v-for="(filter, index) in state.filters"
				:key="index"
				label="Filter by"
				:onRemove="() => state.filters.splice(index, 1)"
			>
				<div
					class="flex items-center divide-x divide-gray-300 overflow-hidden rounded-lg border border-gray-300 text-gray-800"
				>
					<Suspense>
						<ColumnSelector
							:columnOptions="selectedColumns"
							:data_source="query.doc.data_source"
							:tables="selectedTables"
							v-model="filter.column"
						/>
					</Suspense>
					<OperatorSelector
						v-model="filter.operator"
						:column_type="filter.column.type"
						@update:model-value="() => (filter.value = {})"
					/>
					<ValueSelector
						v-if="!filter.operator.value?.includes('is')"
						:column="filter.column"
						:operator="filter.operator"
						v-model="filter.value"
					/>
				</div>
			</QueryBuilderRow>

			<!-- Columns -->
			<QueryBuilderRow
				v-if="state.columns.length"
				v-for="(column, index) in state.columns"
				:key="index"
				label="Select"
				:onRemove="() => state.columns.splice(index, 1)"
			>
				<div
					class="flex items-center divide-x divide-gray-300 overflow-hidden rounded-lg border border-gray-300 text-gray-800"
				>
					<Suspense>
						<ColumnSelector
							:columnOptions="selectedColumns"
							:data_source="query.doc.data_source"
							:tables="selectedTables"
							v-model="column.column"
							@update:model-value="(c) => (column.column.alias = c.label)"
						/>
					</Suspense>
					<InputWithPopover
						v-if="FIELDTYPES.DATE.includes(column.column?.type)"
						:value="findByValue(dateFormatOptions, column.column.granularity)"
						@update:modelValue="(v) => (column.column.granularity = v.value)"
						placeholder="Format"
						:items="dateFormatOptions"
					/>
				</div>
				<div class="h-8 text-sm uppercase leading-8 text-gray-500">as</div>
				<div class="flex rounded-lg border border-gray-300 text-gray-800">
					<ResizeableInput v-model="column.column.alias" placeholder="Label" />
				</div>
			</QueryBuilderRow>

			<!-- Summarise -->
			<QueryBuilderRow v-if="state.measures.length" label="Summarise">
				<div class="flex flex-col space-y-2.5">
					<QueryBuilderRow
						v-for="(measure, index) in state.measures"
						:key="index"
						:onRemove="() => state.measures.splice(index, 1)"
					>
						<div
							class="flex items-center divide-x divide-gray-300 overflow-hidden rounded-lg border border-gray-300 text-gray-800"
						>
							<InputWithPopover
								:value="findByValue(AGGREGATIONS, measure.column.aggregation)"
								placeholder="Aggregate"
								@update:modelValue="(v) => setAggregation(v, measure)"
								:items="AGGREGATIONS"
							/>

							<Suspense v-if="measure.column.aggregation != 'custom'">
								<ColumnSelector
									v-if="measure.column.aggregation !== 'count'"
									:columnOptions="selectedColumns"
									:data_source="query.doc.data_source"
									:tables="selectedTables"
									v-model="measure.column"
									@update:model-value="(c) => (measure.column.alias = c.label)"
								/>
							</Suspense>
							<Suspense v-else>
								<ColumnSelector
									:columnOptions="selectedColumns"
									v-model="measure.column"
									@update:model-value="(c) => (measure.column.alias = c.label)"
								/>
							</Suspense>
						</div>
						<div class="h-8 text-sm uppercase leading-8 text-gray-500">as</div>
						<div class="flex rounded-lg border border-gray-300 text-gray-800">
							<ResizeableInput v-model="measure.column.alias" placeholder="Label" />
						</div>
						<div
							class="!ml-1 cursor-pointer rounded-lg p-1.5 text-gray-400 hover:bg-gray-100"
							@click="state.measures.push({ ...GET_EMPTY_COLUMN() })"
						>
							<FeatherIcon name="plus" class="h-4 w-4" />
						</div>
					</QueryBuilderRow>
				</div>
			</QueryBuilderRow>
			<QueryBuilderRow
				v-if="state.dimensions.length"
				:label="state.measures.length ? 'By' : 'Group by'"
			>
				<div class="flex flex-col space-y-2.5">
					<QueryBuilderRow
						v-for="(dimension, index) in state.dimensions"
						:key="index"
						:onRemove="() => state.dimensions.splice(index, 1)"
					>
						<Suspense>
							<div
								class="flex items-center divide-x divide-gray-300 overflow-hidden rounded-lg border border-gray-300 text-gray-800"
							>
								<ColumnSelector
									v-model="dimension.column"
									:tables="selectedTables"
									:data_source="query.doc.data_source"
									:columnOptions="selectedColumns"
									:columnFilter="(c) => isDimensionColumn(c)"
									@update:model-value="(c) => (dimension.column.alias = c.label)"
								/>
								<InputWithPopover
									v-if="FIELDTYPES.DATE.includes(dimension.column?.type)"
									:value="
										findByValue(dateFormatOptions, dimension.column.granularity)
									"
									@update:modelValue="
										(v) => (dimension.column.granularity = v.value)
									"
									placeholder="Format"
									:items="dateFormatOptions"
								/>
							</div>
						</Suspense>
						<div class="h-8 text-sm uppercase leading-8 text-gray-500">as</div>
						<div class="flex rounded-lg border border-gray-300 text-gray-800">
							<ResizeableInput v-model="dimension.column.alias" placeholder="Label" />
						</div>
						<div
							class="!ml-0.5 cursor-pointer rounded-lg p-1.5 text-gray-400 hover:bg-gray-100"
							@click="state.dimensions.push({ ...GET_EMPTY_COLUMN() })"
						>
							<FeatherIcon name="plus" class="h-4 w-4" />
						</div>
					</QueryBuilderRow>
				</div>
			</QueryBuilderRow>

			<!-- Order By -->
			<QueryBuilderRow
				v-if="state.orders.length"
				v-for="(order, index) in state.orders"
				:key="index"
				label="Sort by"
				:onRemove="() => state.orders.splice(index, 1)"
			>
				<Suspense>
					<ColumnSelector
						class="flex rounded-lg border border-gray-300 text-gray-800"
						:data_source="query.doc.data_source"
						:tables="selectedTables"
						:columnOptions="selectedColumns"
						v-model="order.column"
					/>
				</Suspense>
				<div class="h-8 text-sm uppercase leading-8 text-gray-500">in</div>
				<InputWithPopover
					class="flex rounded-lg border border-gray-300 text-gray-800"
					:value="findByValue(ORDER, order.column.order)"
					placeholder="Ascending"
					:items="ORDER"
					@update:modelValue="(v) => (order.column.order = v.value)"
				/>
				<div class="h-8 text-sm uppercase leading-8 text-gray-500">order</div>
			</QueryBuilderRow>

			<!-- Limit -->
			<QueryBuilderRow
				v-if="state.limit != undefined"
				label="Limit to"
				:onRemove="() => (state.limit = undefined)"
			>
				<div class="flex rounded-lg border border-gray-300 text-gray-800">
					<ResizeableInput v-model="state.limit" placeholder="100" />
				</div>
				<div class="h-8 text-sm uppercase leading-8 text-gray-500">rows</div>
			</QueryBuilderRow>
		</div>

		<div class="flex items-center space-x-1.5 pt-4 text-sm text-gray-400">
			<div
				v-for="item in [
					'Combine',
					'Filter',
					'Select',
					'Calculate',
					'Summarise',
					'Sort',
					'Limit',
				]"
				class="h-7 cursor-pointer rounded-lg border border-gray-300 px-2 text-sm leading-7 transition-all hover:bg-gray-50"
				@click="addBlock(item)"
			>
				{{ item }}
			</div>
		</div>
	</div>
</template>

<style lang="scss">
.cm-editor {
	user-select: text;
	padding: 0px !important;
	background-color: white !important;
}
</style>
