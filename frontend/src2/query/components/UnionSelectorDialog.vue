<script setup lang="ts">
import { computed, inject, reactive } from 'vue'
import { UnionArgs } from '../../types/query.types'
import { workbookKey } from '../../workbook/workbook_key'
import { query_table, table } from '../helpers'
import { Query } from '../query'
import { useTableOptions } from './join_utils'
import { __ } from '../../translation'

const props = defineProps<{ union?: UnionArgs }>()
const emit = defineEmits({
	select: (join: UnionArgs) => true,
})
const showDialog = defineModel()

const union = reactive<UnionArgs>(
	props.union
		? { ...props.union }
		: {
				table: table({}),
				distinct: false,
		  },
)
const selectedTableValue = computed(() => {
	if (union.table.type === 'table' && union.table.table_name) {
		return `${union.table.data_source}.${union.table.table_name}`
	}
	if (union.table.type === 'query' && union.table.query_name) {
		return union.table.query_name
	}
})

function onSelectTable(option: any) {
	if (!option) return
	if (option.data_source && option.table_name) {
		union.table = table({
			data_source: option.data_source,
			table_name: option.table_name,
		})
	}
	if (option.query_name) {
		union.table = query_table({
			workbook: option.workbook,
			query_name: option.query_name,
		})
	}
}

const query = inject('query') as Query
const data_source = computed(() => query.dataSource)

const rightTable = computed(() => {
	return union.table.type === 'table' ? union.table.table_name : ''
})
const tableOptions = useTableOptions({
	data_source,
	initialSearchText: rightTable.value,
})

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
				description: __('Query'),
			}
		})
})

const groupedTableOptions = computed(() => {
	return [
		{
			group: 'Queries',
			options: queryTableOptions.value,
		},
		{
			group: 'Tables',
			options: tableOptions.options,
		},
	]
})

const isValid = computed(() => {
	return (
		(union.table.type === 'table' && union.table.table_name) ||
		(union.table.type === 'query' && union.table.query_name)
	)
})
function confirm() {
	if (!isValid.value) return
	emit('select', { ...union })
	showDialog.value = false
	reset()
}
function reset() {
	Object.assign(union, {
		table: table({}),
		distinct: false,
	})
}
</script>

<template>
	<Dialog :open="showDialog" bare>
		<template #default>
			<div class="rounded-6 bg-surface-base px-4 pb-6 pt-5 sm:px-6">
				<!-- Title & Close -->
				<div class="flex items-center justify-between pb-4">
					<h3 class="text-3xl-semibold leading-6 text-ink-gray-8">
						{{ __('Append Rows') }}
					</h3>
					<Button variant="ghost" @click="showDialog = false" icon="lucide-x" size="md">
					</Button>
				</div>

				<!-- Fields -->
				<div class="flex w-full flex-col gap-3 overflow-auto p-0.5 text-base">
					<div>
						<label class="mb-1 block text-xs text-ink-gray-5">{{
							__('Select Table')
						}}</label>
						<Combobox
							:placeholder="__('Table')"
							:modelValue="selectedTableValue"
							@update:selectedOption="onSelectTable"
							:loading="tableOptions.loading"
							:options="groupedTableOptions"
							@update:query="tableOptions.searchText = $event"
						/>
					</div>
					<div>
						<FormControl
							type="select"
							:label="__('Drop Duplicates')"
							:modelValue="union.distinct ? 'true' : 'false'"
							@update:modelValue="union.distinct = $event === 'true'"
							:options="[
								{ label: __('Yes'), value: 'true' },
								{ label: __('No'), value: 'false' },
							]"
						/>
					</div>
				</div>

				<!-- Actions -->
				<div class="mt-4 flex justify-end gap-2">
					<Button variant="outline" :label="__('Cancel')" @click="showDialog = false" />
					<Button
						variant="solid"
						:label="__('Confirm')"
						:disabled="!isValid"
						@click="confirm"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>
