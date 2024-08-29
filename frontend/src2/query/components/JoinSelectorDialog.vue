<script setup lang="ts">
import { watchDebounced } from '@vueuse/core'
import { Braces } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import JoinFullIcon from '../../components/Icons/JoinFullIcon.vue'
import JoinInnerIcon from '../../components/Icons/JoinInnerIcon.vue'
import JoinLeftIcon from '../../components/Icons/JoinLeftIcon.vue'
import JoinRightIcon from '../../components/Icons/JoinRightIcon.vue'
import useTableStore from '../../data_source/tables'
import { wheneverChanges } from '../../helpers'
import { JoinArgs, JoinType } from '../../types/query.types'
import { column, expression, table } from '../helpers'
import { Query } from '../query'
import InlineExpression from './InlineExpression.vue'

const props = defineProps<{ join?: JoinArgs }>()
const emit = defineEmits({
	select: (join: JoinArgs) => true,
})
const showDialog = defineModel()

// handle backward compatibility
// move left_column and right_column under join_condition
const _props_join: any = props.join
if (props.join && _props_join.left_column?.column_name && _props_join.right_column?.column_name) {
	props.join.join_condition = {
		left_column: _props_join.left_column,
		right_column: _props_join.right_column,
	}
}

const join = ref<JoinArgs>(
	props.join
		? {
				join_type: props.join.join_type,
				table: props.join.table,
				join_condition: props.join.join_condition,
				select_columns: props.join.select_columns || [],
		  }
		: {
				join_type: 'left' as JoinType,
				table: table({
					table_name: '',
					data_source: '',
				}),
				join_condition: {
					left_column: column(''),
					right_column: column(''),
				},
				select_columns: [],
		  }
)

const tableStore = useTableStore()

const query = inject('query') as Query
const data_source = computed(() => {
	// allow only one data source joins for now
	// TODO: support multiple data source joins if live connection is disabled
	// if (!query.doc.use_live_connection) return undefined

	const operations = query.getOperationsForExecution()
	const source = operations.find((op) => op.type === 'source' && 'table' in op)
	return source ? source.table.data_source : undefined
})

type TableOption = {
	label: string
	value: string
	description: string
	data_source: string
	table_name: string
}
const tableOptions = computed<TableOption[]>(() => {
	if (!tableStore.tables.length) return []
	return tableStore.tables.map((t) => ({
		table_name: t.table_name,
		data_source: t.data_source,
		description: t.data_source,
		label: t.table_name,
		value: `${t.data_source}.${t.table_name}`,
	}))
})
const tableSearchText = ref(props.join?.table.table_name || '')
watchDebounced(
	tableSearchText,
	() => tableStore.getTables(data_source.value, tableSearchText.value),
	{
		debounce: 300,
		immediate: true,
	}
)

const tableColumnOptions = ref<DropdownOption[]>([])
const fetchingColumnOptions = ref(false)
wheneverChanges(
	() => join.value.table.table_name,
	() => {
		if (!join.value.table.table_name) return
		fetchingColumnOptions.value = true
		tableStore
			.getTableColumns(join.value.table.data_source, join.value.table.table_name)
			.then((columns) => {
				tableColumnOptions.value = columns.map((c: any) => ({
					label: c.name,
					value: c.name,
					description: c.type,
					data_type: c.type,
				}))
				autoMatchColumns()
			})
			.finally(() => {
				fetchingColumnOptions.value = false
			})
	},
	{ immediate: true }
)

wheneverChanges(
	() => join.value.table.table_name,
	() => {
		if (!join.value.table.table_name) return

		// reset previous values if table is changed
		join.value.select_columns = []
		if (
			'right_column' in join.value.join_condition &&
			join.value.join_condition.right_column.column_name
		) {
			join.value.join_condition.right_column.column_name = ''
		}

		if (
			'join_expression' in join.value.join_condition &&
			join.value.join_condition.join_expression
		) {
			join.value.join_condition.join_expression = expression('')
		}
	}
)

function autoMatchColumns() {
	if ('join_expression' in join.value.join_condition) return

	const selected_tables = query.doc.operations
		.filter((op) => op.type === 'source' || op.type === 'join')
		.map((op) => {
			if (op.type === 'source' && 'table' in op) {
				return op.table.table_name
			}
			if (op.type === 'join' && 'table' in op) {
				return op.table.table_name
			}
			return ''
		})
		.filter((table) => table !== join.value.table.table_name)

	const right_table = join.value.table.table_name
	selected_tables.some(async (left_table: string) => {
		const links = await tableStore.getTableLinks(
			join.value.table.data_source,
			left_table,
			right_table
		)

		if (!links?.length) {
			return false
		}

		// find a link where left column is present in query.result.columns
		const link = links.find((l) => {
			return query.result.columns.find((c) => c.name === l.left_column)
		})
		if (!link) {
			return false
		}

		if ('left_column' in join.value.join_condition) {
			join.value.join_condition.left_column.column_name = link.left_column
			join.value.join_condition.right_column.column_name = link.right_column
		}
	})
}

const showJoinConditionEditor = computed(() => 'join_expression' in join.value.join_condition)
function toggleJoinConditionEditor() {
	if (showJoinConditionEditor.value) {
		join.value.join_condition = {
			left_column: column(''),
			right_column: column(''),
		}
	} else {
		join.value.join_condition = {
			join_expression: expression(''),
		}
	}
}

const isValid = computed(() => {
	const hasValidJoinExpression =
		'join_expression' in join.value.join_condition
			? join.value.join_condition.join_expression.expression
			: false

	const hasValidJoinColumns =
		'left_column' in join.value.join_condition && 'right_column' in join.value.join_condition
			? join.value.join_condition.left_column.column_name &&
			  join.value.join_condition.right_column.column_name
			: false

	return (
		join.value.table.table_name &&
		join.value.join_type &&
		join.value.select_columns.length > 0 &&
		(hasValidJoinExpression || hasValidJoinColumns)
	)
})
function confirm() {
	if (!isValid.value) return
	emit('select', join.value)
	showDialog.value = false
	reset()
}
function reset() {
	join.value = {
		join_type: 'left',
		table: table({
			table_name: '',
			data_source: '',
		}),
		join_condition: {
			left_column: column(''),
			right_column: column(''),
		},
		select_columns: [],
	}
}

const joinTypes = [
	{
		label: 'Left',
		icon: JoinLeftIcon,
		value: 'left',
		description: 'Keep all existing rows and include matching rows from the new table',
	},
	{
		label: 'Inner',
		icon: JoinInnerIcon,
		value: 'inner',
		description: 'Keep only rows that have matching values in both tables',
	},
	{
		label: 'Right',
		icon: JoinRightIcon,
		value: 'right',
		description:
			'Keep all rows from the new table and include matching rows from the existing table',
	},
	{
		label: 'Full',
		icon: JoinFullIcon,
		value: 'full',
		description: 'Keep all rows from both tables',
	},
] as const
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
						<label class="mb-1 block text-xs text-gray-600">Select Table to Join</label>
						<Autocomplete
							placeholder="Table"
							:options="tableOptions"
							:modelValue="
								join.table.table_name
									? `${join.table.data_source}.${join.table.table_name}`
									: ''
							"
							@update:modelValue="
								(option: any) => {
									join.table.data_source = option.data_source
									join.table.table_name = option.table_name
								}
							"
							@update:query="tableSearchText = $event"
							:loading="tableStore.loading"
						/>
					</div>
					<div>
						<label class="mb-1 block text-xs text-gray-600"
							>Select Matching Columns</label
						>
						<div class="flex gap-2">
							<template
								v-if="
									'left_column' in join.join_condition &&
									'right_column' in join.join_condition
								"
							>
								<div class="flex-1">
									<Autocomplete
										placeholder="Column"
										:loading="fetchingColumnOptions"
										:options="query.result.columnOptions"
										:modelValue="join.join_condition.left_column.column_name"
										@update:modelValue="
											join.join_condition.left_column.column_name =
												$event?.value
										"
									/>
								</div>
								<div class="flex flex-shrink-0 items-center font-mono">=</div>
								<div class="flex-1">
									<Autocomplete
										placeholder="Column"
										:loading="fetchingColumnOptions"
										:options="tableColumnOptions"
										:modelValue="join.join_condition.right_column.column_name"
										@update:modelValue="
											join.join_condition.right_column.column_name =
												$event?.value
										"
									/>
								</div>
							</template>
							<template v-else-if="'join_expression' in join.join_condition">
								<InlineExpression v-model="join.join_condition.join_expression" />
							</template>
							<div class="flex flex-shrink-0 items-center">
								<Tooltip text="Custom Join Condition" :hover-delay="0.5">
									<Button @click="toggleJoinConditionEditor">
										<template #icon>
											<Braces
												class="h-4 w-4 text-gray-700"
												stroke-width="1.5"
											/>
										</template>
									</Button>
								</Tooltip>
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
							:loading="fetchingColumnOptions"
							:options="tableColumnOptions"
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
