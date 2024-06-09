<script setup>
import DraggableList from '@/components/DraggableList.vue'
import { Combine } from 'lucide-vue-next'
import { computed, inject, nextTick, ref } from 'vue'
import ColumnExpressionEditor from './ColumnExpressionEditor.vue'
import ColumnListItem from './ColumnListItem.vue'
import SectionHeader from './SectionHeader.vue'
import SimpleColumnEditor from './SimpleColumnEditor.vue'
import { NEW_COLUMN } from './constants'

const query = inject('query')
const assistedQuery = inject('assistedQuery')
!assistedQuery.columnOptions.length && assistedQuery.fetchColumnOptions()

const columns = computed({
	get: () => assistedQuery.columns,
	set: (value) => (assistedQuery.columns = value),
})
const columnRefs = ref(null)
const activeColumnIdx = ref(null)
const showExpressionEditor = computed(() => {
	if (activeColumnIdx.value === null) return false
	const activeColumn = columns.value[activeColumnIdx.value]
	return isExpressionColumn(activeColumn)
})
const showSimpleColumnEditor = computed(() => {
	if (activeColumnIdx.value === null) return false
	return !showExpressionEditor.value
})
function isExpressionColumn(column) {
	return column.expression.hasOwnProperty('raw') || column.expression.hasOwnProperty('ast')
}

function onColumnSelect(column) {
	if (!column) return
	const columnAlreadyExists = columns.value.find(
		(c) => c.table === column.table && c.column === column.column && c.label === column.label
	)
	if (columnAlreadyExists) {
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
	nextTick(() => {
		activeColumnIdx.value = columns.value.length - 1
	})
}

function onColumnSort(e) {
	if (e.oldIndex != e.newIndex) {
		assistedQuery.moveColumn(e.oldIndex, e.newIndex)
	}
}
</script>

<template>
	<div class="space-y-2">
		<SectionHeader
			title="Columns"
			:icon="Combine"
			info="Select the columns you want to see in the results."
		>
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
		</SectionHeader>
		<DraggableList
			v-if="columns.length"
			v-model:items="columns"
			group="columns"
			item-key="label"
			:showEmptyState="true"
			:showHandle="false"
		>
			<template #item="{ item: column, index: idx }">
				<ColumnListItem
					v-if="isExpressionColumn(column)"
					:column="column"
					:isActive="activeColumnIdx === idx"
					@edit-column="activeColumnIdx = idx"
					@remove-column="assistedQuery.removeColumnAt(idx)"
				/>
				<Popover
					v-else
					:show="showSimpleColumnEditor && activeColumnIdx === idx"
					@close="activeColumnIdx === idx ? (activeColumnIdx = null) : null"
					placement="right-start"
				>
					<template #target="{ togglePopover }">
						<ColumnListItem
							:column="column"
							:isActive="activeColumnIdx === idx"
							@edit-column="activeColumnIdx = idx"
							@remove-column="assistedQuery.removeColumnAt(idx)"
						/>
					</template>
					<template #body>
						<div
							v-if="showSimpleColumnEditor && activeColumnIdx === idx"
							class="ml-2 w-[20rem] rounded-lg border border-gray-100 bg-white text-base shadow-xl"
						>
							<SimpleColumnEditor
								:column="column"
								@remove="onRemoveColumn"
								@save="onSaveColumn"
								@discard="activeColumnIdx = null"
							/>
						</div>
					</template>
				</Popover>
			</template>
		</DraggableList>
	</div>

	<Dialog :modelValue="showExpressionEditor" :options="{ size: '3xl' }">
		<template #body>
			<div class="bg-white px-4 pb-6 pt-5 sm:px-6">
				<div class="flex items-center justify-between pb-4">
					<h3 class="text-2xl font-semibold leading-6 text-gray-900">
						Column Expression
					</h3>
					<Button variant="ghost" @click="activeColumnIdx = null" icon="x"> </Button>
				</div>
				<ColumnExpressionEditor
					:column="columns[activeColumnIdx]"
					@remove="onRemoveColumn"
					@save="onSaveColumn"
				/>
			</div>
		</template>
	</Dialog>
</template>
