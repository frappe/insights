<script setup lang="ts">
import JoinFullIcon from '@/components/Icons/JoinFullIcon.vue'
import JoinInnerIcon from '@/components/Icons/JoinInnerIcon.vue'
import JoinLeftIcon from '@/components/Icons/JoinLeftIcon.vue'
import JoinRightIcon from '@/components/Icons/JoinRightIcon.vue'
import { wheneverChanges } from '@/utils'
import { watchDebounced } from '@vueuse/core'
import { computed, inject, ref } from 'vue'
import useTableStore from '../../data_source/tables'
import { JoinArgs, JoinType } from '../../types/query.types'
import { column, table } from '../helpers'
import { Query } from '../query'

const props = defineProps<{ join?: JoinArgs }>()
const emit = defineEmits({
	select: (join: JoinArgs) => true,
})
const showDialog = defineModel()

const join = ref<JoinArgs>(
	props.join
		? {
				join_type: props.join.join_type,
				table: table({
					table_name: props.join.table.table_name,
					data_source: props.join.table.data_source,
				}),
				left_column: column(props.join.left_column.column_name),
				right_column: column(props.join.right_column.column_name),
		  }
		: {
				join_type: 'left' as JoinType,
				table: table({
					table_name: '',
					data_source: '',
				}),
				left_column: column(''),
				right_column: column(''),
		  }
)

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
const tableSearchText = ref(props.join?.table.table_name || '')
watchDebounced(tableSearchText, () => tableStore.getTables(undefined, tableSearchText.value), {
	debounce: 300,
	immediate: true,
})

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

				if (join.value.right_column.column_name) {
					join.value.right_column.column_name = ''
				}

				autoMatchColumns()
			})
			.finally(() => {
				fetchingColumnOptions.value = false
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
		join.value.left_column.column_name = matchingColumns[0].value
		join.value.right_column.column_name = matchingColumns[0].value
	}
}

const isValid = computed(() => {
	return (
		join.value.table.table_name &&
		join.value.left_column.column_name &&
		join.value.right_column.column_name &&
		join.value.join_type
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
		left_column: column(''),
		right_column: column(''),
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
					<label class="mb-1 block text-xs text-gray-600">Pick Matching Columns</label>
					<div class="flex gap-2">
						<div class="flex-1">
							<Autocomplete
								placeholder="Column"
								:loading="fetchingColumnOptions"
								:options="query.result.columnOptions"
								:modelValue="join.left_column.column_name"
								@update:modelValue="join.left_column.column_name = $event?.value"
							/>
						</div>
						<div class="flex flex-shrink-0 items-center font-mono">=</div>
						<div class="flex-1">
							<Autocomplete
								placeholder="Column"
								:loading="fetchingColumnOptions"
								:options="tableColumnOptions"
								:modelValue="join.right_column.column_name"
								@update:modelValue="join.right_column.column_name = $event?.value"
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
			</div>
		</template>
	</Dialog>
</template>
