<script setup lang="ts">
import { Braces } from 'lucide-vue-next'
import { computed, inject, reactive, watch } from 'vue'
import useTableStore from '../../data_source/tables'
import { wheneverChanges } from '../../helpers'
import { joinTypes } from '../../helpers/constants'
import { JoinArgs } from '../../types/query.types'
import { workbookKey } from '../../workbook/workbook'
import { column, expression, query_table, table } from '../helpers'
import useQuery, { Query } from '../query'
import InlineExpression from './InlineExpression.vue'
import { handleOldProps, useTableColumnOptions, useTableOptions } from './join_utils'

const props = defineProps<{ join?: JoinArgs }>()
const emit = defineEmits({
	select: (join: JoinArgs) => true,
})
const showDialog = defineModel()

if (props.join) {
	handleOldProps(props.join)
}

const join = reactive<JoinArgs>(
	props.join
		? { ...props.join }
		: {
				join_type: 'inner',
				table: table({}),
				join_condition: {
					left_column: column(''),
					right_column: column(''),
				},
				select_columns: [],
		  }
)
const selectedTable = computed({
	get() {
		if (join.table.type === 'table' && join.table.table_name) {
			return `${join.table.data_source}.${join.table.table_name}`
		}
		if (join.table.type === 'query' && join.table.query_name) {
			return join.table.query_name
		}
	},
	set(option: any) {
		if (option.data_source && option.table_name) {
			join.table = table({
				data_source: option.data_source,
				table_name: option.table_name,
			})
		}
		if (option.query_name) {
			join.table = query_table({
				workbook: option.workbook,
				query_name: option.query_name,
			})
		}
	},
})

const query = inject('query') as Query
const data_source = computed(() => query.dataSource)

wheneverChanges(selectedTable, () => {
	if (!selectedTable.value) return

	// reset previous values if table is changed
	join.select_columns = []
	if ('right_column' in join.join_condition && join.join_condition.right_column.column_name) {
		join.join_condition.right_column.column_name = ''
	}

	if ('join_expression' in join.join_condition && join.join_condition.join_expression) {
		join.join_condition.join_expression = expression('')
	}
})

const rightTable = computed(() => {
	return join.table.type === 'table' ? join.table.table_name : ''
})
const tableOptions = useTableOptions({
	data_source,
	initialSearchText: rightTable.value,
})
const rightTableColumnOptions = useTableColumnOptions(data_source, rightTable)

watch(
	() => rightTableColumnOptions.options,
	() => {
		if ('join_expression' in join.join_condition) return
		if (!rightTableColumnOptions.options.length) return

		if (
			'right_column' in join.join_condition &&
			!join.join_condition.right_column.column_name
		) {
			autoMatchColumns()
		}
	}
)

const tableStore = useTableStore()
async function autoMatchColumns() {
	const selected_tables = query.currentOperations
		.filter((op) => op.type === 'source' || op.type === 'join')
		.map((op) => {
			if (op.type === 'source' && op.table.type === 'table') {
				return op.table.table_name
			}
			if (op.type === 'join' && op.table.type === 'table') {
				return op.table.table_name
			}
			return ''
		})
		.filter((table) => table !== rightTable.value)

	const right_table = rightTable.value
	const resultColumns = query.result.columns.map((c) => c.name)
	for (const left_table of selected_tables) {
		const links = await tableStore.getTableLinks(data_source.value, left_table, right_table)
		if (!links?.length) {
			continue
		}
		// find a link where left column is present in query.result.columns
		const link = links.find((l) => resultColumns.includes(l.left_column))
		if (!link) continue
		if ('left_column' in join.join_condition) {
			join.join_condition.left_column.column_name = link.left_column
			join.join_condition.right_column.column_name = link.right_column
			break
		}
	}
}

const workbook = inject(workbookKey)!
const queryTableOptions = computed(() => {
	const linkedQueries = workbook.getLinkedQueries(query.doc.name)
	return workbook.doc.queries
		.filter((q) => q.name !== query.doc.name && !linkedQueries.includes(q.name))
		.map((q) => {
			return {
				workbook: workbook.doc.name,
				query_name: q.name,
				label: q.title,
				value: q.name,
				description: 'Query',
			}
		})
})
const groupedTableOptions = computed(() => {
	return [
		{
			group: 'Queries',
			items: queryTableOptions.value,
		},
		{
			group: 'Tables',
			items: tableOptions.options,
		},
	]
})

const queryTableColumnOptions = computed(() => {
	if (join.table.type !== 'query') return []
	const query = useQuery(join.table.query_name)
	return query.result.columnOptions
})

const showJoinConditionEditor = computed(() => 'join_expression' in join.join_condition)
function toggleJoinConditionEditor() {
	if (showJoinConditionEditor.value) {
		join.join_condition = {
			left_column: column(''),
			right_column: column(''),
		}
	} else {
		join.join_condition = {
			join_expression: expression(''),
		}
	}
}

const isValid = computed(() => {
	const isRightTableSelected =
		(join.table.type === 'table' && join.table.table_name) ||
		(join.table.type === 'query' && join.table.query_name)

	const hasValidJoinExpression =
		'join_expression' in join.join_condition
			? join.join_condition.join_expression.expression
			: false

	const hasValidJoinColumns =
		'left_column' in join.join_condition && 'right_column' in join.join_condition
			? join.join_condition.left_column.column_name &&
			  join.join_condition.right_column.column_name
			: false

	return (
		isRightTableSelected &&
		join.join_type &&
		join.select_columns.length > 0 &&
		(hasValidJoinExpression || hasValidJoinColumns)
	)
})
function confirm() {
	if (!isValid.value) return
	emit('select', { ...join })
	showDialog.value = false
	reset()
}
function reset() {
	Object.assign(join, {
		join_type: 'inner',
		table: table({}),
		join_condition: {
			left_column: column(''),
			right_column: column(''),
		},
		select_columns: [],
	})
}
</script>

<template>
	<Dialog :modelValue="showDialog">
		<template #body>
			<div class="rounded-lg bg-white px-4 pb-6 pt-5 sm:px-6">
				<!-- Title & Close -->
				<div class="flex items-center justify-between pb-4">
					<h3 class="text-2xl font-semibold leading-6 text-gray-900">Join Table</h3>
					<Button variant="ghost" @click="showDialog = false" icon="x" size="md">
					</Button>
				</div>

				<!-- Fields -->
				<div class="flex w-full flex-col gap-3 overflow-auto p-0.5 text-base">
					<div>
						<Autocomplete
							label="Right Table"
							placeholder="Table"
							v-model="selectedTable"
							:loading="tableOptions.loading"
							:options="groupedTableOptions"
							@update:query="tableOptions.searchText = $event"
						/>
					</div>
					<div>
						<div class="flex items-end gap-2">
							<template
								v-if="
									'left_column' in join.join_condition &&
									'right_column' in join.join_condition
								"
							>
								<div class="flex-1">
									<Autocomplete
										label="Left Column"
										placeholder="Column"
										:options="query.result.columnOptions"
										:modelValue="join.join_condition.left_column.column_name"
										@update:modelValue="
											join.join_condition.left_column.column_name =
												$event?.value
										"
									/>
								</div>
								<div class="flex h-7 flex-shrink-0 items-center font-mono">=</div>
								<div class="flex-1">
									<Autocomplete
										label="Right Column"
										placeholder="Column"
										:loading="rightTableColumnOptions.loading"
										:options="[
											...rightTableColumnOptions.options,
											...queryTableColumnOptions,
										]"
										:modelValue="join.join_condition.right_column.column_name"
										@update:modelValue="
											join.join_condition.right_column.column_name =
												$event?.value
										"
									/>
								</div>
							</template>
							<template v-else-if="'join_expression' in join.join_condition">
								<div class="flex-1">
									<label class="mb-1 block text-xs text-gray-600"
										>Custom Join Condition
									</label>
									<InlineExpression
										v-model="join.join_condition.join_expression"
										placeholder="Example: (t1.column_name = t2.column_name) & (t1.column_name > 10)"
									/>
								</div>
							</template>
							<div class="flex flex-shrink-0 items-start">
								<Button @click="toggleJoinConditionEditor">
									<template #icon>
										<Braces class="h-4 w-4 text-gray-700" stroke-width="1.5" />
									</template>
								</Button>
							</div>
						</div>
					</div>
					<div>
						<label class="mb-1 block text-xs text-gray-600">Select Join Type</label>
						<div class="flex gap-2">
							<div
								v-for="joinType in joinTypes"
								:key="joinType.label"
								class="flex flex-1 flex-col items-center justify-center rounded border py-3 transition-all"
								:class="
									join.join_type === joinType.value
										? 'border-gray-700'
										: 'cursor-pointer hover:border-gray-400'
								"
								@click="join.join_type = joinType.value"
							>
								<component
									:is="joinType.icon"
									class="h-6 w-6 text-gray-600"
									stroke-width="1.5"
								/>
								<span class="block text-center text-xs">{{ joinType.label }}</span>
							</div>
						</div>
						<div class="mt-1 text-xs text-gray-600">
							{{ joinTypes.find((j) => j.value === join.join_type)?.description }}
						</div>
					</div>
					<div>
						<label class="mb-1 block text-xs text-gray-600"
							>Select Columns to Add</label
						>
						<Autocomplete
							:multiple="true"
							placeholder="Columns"
							:loading="rightTableColumnOptions.loading"
							:options="[
								...rightTableColumnOptions.options,
								...queryTableColumnOptions,
							]"
							:modelValue="join.select_columns?.map((c) => c.column_name)"
							@update:modelValue="
								join.select_columns = $event?.map((o: any) => column(o.value)) || []
							"
						/>
					</div>
				</div>

				<!-- Actions -->
				<div class="mt-4 flex justify-end gap-2">
					<Button variant="outline" label="Cancel" @click="showDialog = false" />
					<Button variant="solid" label="Confirm" :disabled="!isValid" @click="confirm" />
				</div>
			</div>
		</template>
	</Dialog>
</template>
