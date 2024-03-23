<script setup lang="ts">
import JoinFullIcon from '@/components/Icons/JoinFullIcon.vue'
import JoinInnerIcon from '@/components/Icons/JoinInnerIcon.vue'
import JoinLeftIcon from '@/components/Icons/JoinLeftIcon.vue'
import JoinRightIcon from '@/components/Icons/JoinRightIcon.vue'
import useDataSource from '@/datasource/useDataSource'
import useDataSourceTable from '@/datasource/useDataSourceTable'
import { computed, inject, ref, watch } from 'vue'
import { QueryPipeline } from './useQueryPipeline'
import { column, table } from './pipeline_utils'

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

const queryPipeline = inject('queryPipeline') as QueryPipeline

const dataSource = useDataSource(queryPipeline.dataSource)
dataSource.fetchTables()
const tableOptions = computed(() => {
	const tableGroup = dataSource.groupedTableOptions.find((group) => group.group == 'Tables')
	if (!tableGroup) return []
	return tableGroup.items
})

const tableColumnOptions = ref<DropdownOption[]>([])
watch(
	() => join.value.table,
	// @ts-ignore
	async (newTable: string, oldTable: string) => {
		if (!newTable) return
		if (newTable === oldTable) return
		const rightTable = await useDataSourceTable({
			data_source: queryPipeline.dataSource,
			table: newTable,
		})
		tableColumnOptions.value = rightTable.columns.map((c) => ({
			label: c.column,
			value: c.column,
			description: c.type,
		}))
		if (join.value.rightColumn) {
			join.value.rightColumn = ''
		}
	},
	{ immediate: true }
)

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
	emit('select', {
		table: table(join.value.table),
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
		v-if="showDialog"
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
								:options="queryPipeline.results.columnOptions"
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
