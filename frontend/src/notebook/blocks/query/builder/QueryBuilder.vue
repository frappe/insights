<script setup>
import { isDimensionColumn } from '@/utils'
import { computed, inject } from 'vue'
import ColumnExpressionSelector from './ColumnExpressionSelector.vue'
import ColumnSelector from './ColumnSelector.vue'
import InputWithPopover from './InputWithPopover.vue'
import MultipleColumnSelector from './MultipleColumnSelector.vue'
import OperatorSelector from './OperatorSelector.vue'
import QueryBuilderRow from './QueryBuilderRow.vue'
import ResizeableInput from './ResizeableInput.vue'
import TableSelector from './TableSelector.vue'
import ValueSelector from './ValueSelector.vue'

const query = inject('query')

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

function addBlock(type) {
	if (type == 'Join') {
		state.value.joins.push({
			left_table: {},
			right_table: {},
			join_type: { label: 'Inner', value: 'inner' },
			left_column: {},
			right_column: {},
		})
	}
	if (type == 'Filter') {
		state.value.filters.push({
			column: {},
			operator: {},
			value: {},
		})
	}
	if (type == 'Column') {
		state.value.columns.push({
			column: {},
		})
	}
	if (type == 'Sort') {
		state.value.order_by.push({
			column: {},
			order: {
				label: 'Ascending',
				value: 'asc',
			},
		})
	}
	if (type == 'Limit') {
		state.value.limit = 10
	}
	if (type == 'Calculate') {
		state.value.calculations.push({
			alias: '',
			expression: {},
		})
	}
	if (type == 'Summarise') {
		if (state.value.summarise.metrics) return
		state.value.summarise = {
			metrics: [{ aggregation: {}, column: {} }],
			dimensions: [{ column: {} }],
		}
	}
}

function isColumnSelected(column) {
	return state.value.columns.some((c) => c.column.column == column.column)
}
function isDimensionSelected(column) {
	return state.value.summarise.dimensions.some((d) => d.column.column == column.column)
}
</script>

<template>
	<div class="flex flex-1 flex-col justify-between px-3 py-1 text-base">
		<div
			v-if="query.doc.data_source"
			class="space-y-3 overflow-scroll scrollbar-hide"
			:key="query.doc.data_source"
		>
			<QueryBuilderRow label="Start with">
				<TableSelector
					class="flex rounded-lg border border-gray-300 text-gray-800"
					:data_source="query.doc.data_source"
					v-model="state.table"
				/>
			</QueryBuilderRow>

			<!-- Joins -->
			<QueryBuilderRow
				v-if="state.joins.length"
				v-for="(join, index) in state.joins"
				:key="index"
				label="Join"
				:onRemove="() => state.joins.splice(index, 1)"
			>
				<InputWithPopover
					class="flex rounded-lg border border-gray-300 text-gray-800"
					placeholder="Pick a table"
					v-model="join.left_table"
					:items="selectedTables"
				></InputWithPopover>
				<div class="text-sm uppercase text-gray-500">with</div>
				<TableSelector
					class="flex rounded-lg border border-gray-300 text-gray-800"
					:data_source="query.doc.data_source"
					v-model="join.right_table"
				/>
				<div class="text-sm uppercase text-gray-500">where</div>
				<Suspense>
					<ColumnSelector
						class="flex rounded-lg border border-gray-300 text-gray-800"
						:data_source="query.doc.data_source"
						:tables="[join.left_table]"
						v-model="join.left_column"
					/>
				</Suspense>
				<div class="text-sm uppercase text-gray-500">=</div>
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
				<ResizeableInput
					class="flex rounded-lg border border-gray-300 text-gray-800"
					v-model="calc.alias"
					placeholder="Alias"
				/>
				<div class="text-sm uppercase text-gray-500">as</div>
				<ColumnExpressionSelector
					class="flex rounded-lg border border-gray-300 text-gray-800"
					v-model="calc.expression"
				/>
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
							:data_source="query.doc.data_source"
							:tables="selectedTables"
							v-model="filter.column"
						/>
					</Suspense>
					<OperatorSelector :column_type="filter.column.type" v-model="filter.operator" />
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
				label="Pick"
				:onRemove="() => state.columns.splice(index, 1)"
			>
				<Suspense>
					<ColumnSelector
						class="flex rounded-lg border border-gray-300 text-gray-800"
						:data_source="query.doc.data_source"
						:tables="selectedTables"
						v-model="column.column"
						:columnFilter="(c) => !isColumnSelected(c)"
					/>
				</Suspense>
				<div class="text-sm uppercase text-gray-500">as</div>
				<ResizeableInput
					class="flex rounded-lg border border-gray-300 text-gray-800"
					v-model="column.alias"
					placeholder="Alias"
				/>
			</QueryBuilderRow>

			<!-- Summarise -->
			<div v-if="state.summarise.metrics?.length" class="flex flex-col space-y-2.5 text-base">
				<QueryBuilderRow label="Summarise" :onRemove="() => (state.summarise = {})">
					<div
						class="flex items-center"
						v-for="(column, index) in state.summarise.metrics"
						:key="index"
					>
						<div
							class="flex items-center divide-x divide-gray-300 overflow-hidden rounded-lg border border-gray-300 text-gray-800"
						>
							<InputWithPopover
								v-model="column.aggregation"
								placeholder="Count"
								:disable-filter="true"
								:items="[
									{ label: 'Count of Records', value: 'count' },
									{ label: 'Sum', value: 'sum' },
									{ label: 'Average', value: 'avg' },
									{ label: 'Minimum', value: 'min' },
									{ label: 'Maximum', value: 'max' },
								]"
							/>

							<Suspense>
								<ColumnSelector
									v-if="
										column.aggregation?.value &&
										column.aggregation.value !== 'count'
									"
									:data_source="query.doc.data_source"
									:tables="selectedTables"
									v-model="column.column"
								/>
							</Suspense>
						</div>
					</div>
					<div
						class="!ml-0.5 cursor-pointer rounded-lg p-1.5 text-gray-400 hover:bg-gray-100"
						@click="state.summarise.metrics.push({ aggregation: {}, column: {} })"
					>
						<FeatherIcon name="plus" class="h-4 w-4" />
					</div>
				</QueryBuilderRow>
				<QueryBuilderRow label="By">
					<MultipleColumnSelector
						v-model="state.summarise.dimensions"
						:data_source="query.doc.data_source"
						:tables="selectedTables"
						:columnFilter="(c) => isDimensionColumn(c) && !isDimensionSelected(c)"
					/>
					<div
						class="!ml-0.5 cursor-pointer rounded-lg p-1.5 text-gray-400 hover:bg-gray-100"
						@click="state.summarise.dimensions.push({ column: {} })"
					>
						<FeatherIcon name="plus" class="h-4 w-4" />
					</div>
				</QueryBuilderRow>
			</div>

			<!-- Order By -->
			<QueryBuilderRow
				v-if="state.order_by.length"
				v-for="(column, index) in state.order_by"
				:key="index"
				label="Sort by"
				:onRemove="() => state.order_by.splice(index, 1)"
			>
				<Suspense>
					<ColumnSelector
						class="flex rounded-lg border border-gray-300 text-gray-800"
						:data_source="query.doc.data_source"
						:tables="selectedTables"
						v-model="column.column"
					/>
				</Suspense>
				<div class="text-sm uppercase text-gray-500">in</div>
				<InputWithPopover
					class="flex rounded-lg border border-gray-300 text-gray-800"
					v-model="column.order"
					:disable-filter="true"
					:items="[
						{ value: 'asc', label: 'Ascending' },
						{ value: 'desc', label: 'Descending' },
					]"
				/>
				<div class="text-sm uppercase text-gray-500">order</div>
			</QueryBuilderRow>

			<!-- Limit -->
			<QueryBuilderRow
				v-if="state.limit != undefined"
				label="Limit to"
				:onRemove="() => (state.limit = undefined)"
			>
				<ResizeableInput
					class="flex rounded-lg border border-gray-300 text-gray-800"
					v-model="state.limit"
					placeholder="100"
				/>
				<div class="text-sm uppercase text-gray-500">rows</div>
			</QueryBuilderRow>
		</div>

		<div class="flex items-center space-x-1.5 pt-4 text-sm text-gray-400">
			<FeatherIcon name="plus" class="mr-1 h-4 w-4" />
			<div
				v-for="item in [
					'Join',
					'Filter',
					'Column',
					'Calculate',
					'Summarise',
					'Sort',
					'Limit',
				]"
				class="cursor-pointer rounded-lg border border-gray-300 px-2 py-0.5 transition-all hover:bg-gray-50"
				@click="addBlock(item)"
			>
				{{ item }}
			</div>
		</div>
	</div>
</template>
