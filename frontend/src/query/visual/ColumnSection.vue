<script setup>
import UsePopover from '@/components/UsePopover.vue'
import { Combine, X } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import ColumnEditor from './ColumnEditor.vue'
import { NEW_COLUMN } from './constants'

const query = inject('query')
const assistedQuery = inject('assistedQuery')
!assistedQuery.columnOptions.length && assistedQuery.fetchColumnOptions()

const columns = computed(() => assistedQuery.columns)
const columnRefs = ref(null)
const activeColumnIdx = ref(null)

function onColumnSelect(column) {
	if (!column) return
	if (columns.value.find((c) => c.table === column.table && c.column === column.column)) {
		return
	}
	assistedQuery.addColumns([column])
}

function onRemoveColumn() {
	assistedQuery.removeColumnAt(activeColumnIdx.value)
	activeColumnIdx.value = null
}
function onSaveColumn(column) {
	assistedQuery.updateColumnAt(activeColumnIdx.value, column)
	activeColumnIdx.value = null
}
function onAddColumnExpression() {
	assistedQuery.addColumns([
		{
			...NEW_COLUMN,
			expression: {
				raw: '',
				ast: {},
			},
		},
	])
	activeColumnIdx.value = columns.value.length - 1
}
function isValidColumn(column) {
	const isExpression = column.expression?.raw
	return column.label && column.type && (isExpression || (column.table && column.column))
}

const aggregationToAbbr = {
	min: 'MIN',
	max: 'MAX',
	sum: 'SUM',
	avg: 'AVG',
	count: 'CNT',
	distinct: 'UDST',
	distinct_count: 'DCNT',
	'group by': 'UNQ',
	'cumulative count': 'CCNT',
	'cumulative sum': 'CSUM',
}
function getAbbreviation(column) {
	if (column.expression?.raw) return 'EXPR'
	return aggregationToAbbr[column.aggregation] || 'UNQ'
}
</script>

<template>
	<div>
		<div class="mb-2 flex items-center justify-between">
			<div class="flex items-center space-x-1.5">
				<Combine class="h-4 w-4 text-gray-600" />
				<p class="font-medium">Summarize</p>
			</div>
			<Autocomplete
				:modelValue="columns"
				bodyClasses="w-[18rem]"
				@update:modelValue="onColumnSelect"
				:options="assistedQuery.groupedColumnOptions"
				@update:query="assistedQuery.fetchColumnOptions"
			>
				<template #target="{ togglePopover }">
					<Button variant="outline" icon="plus" @click="togglePopover"></Button>
				</template>
				<template #footer="{ togglePopover }">
					<Button
						class="w-full"
						variant="ghost"
						iconLeft="plus"
						@click="onAddColumnExpression() || togglePopover()"
					>
						Custom Expression
					</Button>
				</template>
			</Autocomplete>
		</div>
		<div class="space-y-2">
			<div
				ref="columnRefs"
				v-for="(column, idx) in columns"
				:key="idx"
				class="group flex h-8 cursor-pointer items-center justify-between rounded border border-gray-300 bg-white px-2 hover:shadow"
				:class="
					activeColumnIdx === idx
						? 'border-gray-500 bg-white shadow-sm ring-1 ring-gray-400'
						: ''
				"
				@click="activeColumnIdx = columns.indexOf(column)"
			>
				<div class="flex w-full items-center overflow-hidden">
					<div
						class="flex w-full items-center space-x-1.5 truncate"
						v-if="isValidColumn(column)"
					>
						<div
							class="rounded border border-violet-400 py-0.5 px-1 font-mono text-xs tracking-wider text-violet-700"
						>
							{{ getAbbreviation(column) }}
						</div>
						<div>{{ column.label }}</div>
					</div>
					<div v-else class="text-gray-600">Select a column</div>
				</div>
				<div class="flex items-center space-x-2">
					<X
						class="invisible h-4 w-4 text-gray-600 transition-all hover:text-gray-800 group-hover:visible"
						@click.prevent.stop="assistedQuery.removeColumnAt(idx)"
					/>
				</div>
			</div>
		</div>
	</div>

	<UsePopover
		v-if="columnRefs?.[activeColumnIdx]"
		:show="activeColumnIdx !== null"
		@update:show="activeColumnIdx = null"
		:target-element="columnRefs[activeColumnIdx]"
	>
		<div class="w-[20rem] rounded bg-white text-base shadow-2xl">
			<ColumnEditor
				:column="columns[activeColumnIdx]"
				@discard="activeColumnIdx = null"
				@remove="onRemoveColumn"
				@save="onSaveColumn"
			/>
		</div>
	</UsePopover>
</template>
