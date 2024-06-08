<script setup lang="ts">
import JoinFullIcon from '@/components/Icons/JoinFullIcon.vue'
import JoinInnerIcon from '@/components/Icons/JoinInnerIcon.vue'
import JoinLeftIcon from '@/components/Icons/JoinLeftIcon.vue'
import JoinRightIcon from '@/components/Icons/JoinRightIcon.vue'
import { wheneverChanges } from '@/utils'
import { computed, inject, ref } from 'vue'
import useTableStore from '../../data_source/tables'
import { column, table } from '../helpers'
import { Query } from '../query'

const emit = defineEmits({
	select: (join: JoinArgs) => true,
})
const showDialog = defineModel()

const join = ref({
	type: 'left' as JoinType,
	table: '',
	leftColumn: '',
	rightColumn: '',
})

const tableStore = useTableStore()
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

const tableColumnOptions = ref<DropdownOption[]>([])
wheneverChanges(
	() => join.value.table,
	() => {
		const newTable = join.value.table
		const tableColumn = tableOptions.value.find((t) => t.value === newTable) as TableOption
		tableStore
			.getTableColumns(tableColumn.data_source, tableColumn.table_name)
			.then((columns) => {
				tableColumnOptions.value = columns.map((c) => ({
					label: c.name,
					value: c.name,
					description: c.type,
					data_type: c.type,
				}))

				if (join.value.rightColumn) {
					join.value.rightColumn = ''
				}

				autoMatchColumns()
			})
	},
	{ immediate: true }
)

const query = inject('query') as Query
function autoMatchColumns() {
	if (!join.value.table) return
	const leftColumns = query.result.columnOptions
	const rightColumns = tableColumnOptions.value
	const matchingColumns = leftColumns.filter((l) => rightColumns.some((r) => r.value === l.value))
	if (matchingColumns.length) {
		join.value.leftColumn = matchingColumns[0].value
		join.value.rightColumn = matchingColumns[0].value
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
]

const isValid = computed(() => {
	return join.value.table && join.value.leftColumn && join.value.rightColumn && join.value.type
})
function confirm() {
	if (!isValid.value) return
	const tableOption = tableOptions.value.find((t) => t.value === join.value.table) as TableOption
	emit('select', {
		table: table(tableOption.data_source, tableOption.table_name),
		left_column: column(join.value.leftColumn),
		right_column: column(join.value.rightColumn),
		join_type: join.value.type,
	})
	reset()
	showDialog.value = false
}
function reset() {
	join.value = {
		type: 'left',
		table: '',
		leftColumn: '',
		rightColumn: '',
	}
}
</script>

<template>
	<Dialog
		v-model="showDialog"
		@after-leave="reset"
		:options="{
			title: 'Join Table',
			actions: [
				{
					label: 'Confirm',
					variant: 'solid',
					disabled: !isValid,
					onClick: confirm,
				},
			],
		}"
	>
		<template #body-content>
			<div class="-mb-5 flex flex-col gap-3 overflow-auto p-0.5 text-base">
				<div>
					<label class="mb-1 block text-xs text-gray-600">Pick Table to Join</label>
					<Autocomplete
						placeholder="Table"
						:options="tableOptions"
						:modelValue="join.table"
						@update:modelValue="join.table = $event.value"
					/>
				</div>
				<div>
					<label class="mb-1 block text-xs text-gray-600">Pick Matching Columns</label>
					<div class="flex gap-2">
						<div class="flex-1">
							<Autocomplete
								placeholder="Column"
								:options="query.result.columnOptions"
								:modelValue="join.leftColumn"
								@update:modelValue="join.leftColumn = $event.value"
							/>
						</div>
						<div class="flex flex-shrink-0 items-center font-mono">=</div>
						<div class="flex-1">
							<Autocomplete
								placeholder="Column"
								:options="tableColumnOptions"
								:modelValue="join.rightColumn"
								@update:modelValue="join.rightColumn = $event.value"
							/>
						</div>
					</div>
				</div>
				<div>
					<label class="mb-1 block text-xs text-gray-600">Pick Join Type</label>
					<div class="flex gap-2">
						<div
							v-for="joinType in joinTypes"
							:key="joinType.label"
							class="flex flex-1 flex-col items-center justify-center rounded border py-3 transition-all"
							:class="
								join.type === joinType.value
									? 'border-gray-700'
									: 'cursor-pointer hover:border-gray-400'
							"
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
						{{ joinTypes.find((j) => j.value === join.type)?.description }}
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
