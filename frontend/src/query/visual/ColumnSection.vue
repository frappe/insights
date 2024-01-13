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

const columns = computed(() => assistedQuery.columns)
const columnRefs = ref(null)
const activeColumnIdx = ref(null)
const showExpressionEditor = computed(() => {
	if (activeColumnIdx.value === null) return false
	const activeColumn = columns.value[activeColumnIdx.value]
	return (
		activeColumn.expression.hasOwnProperty('raw') ||
		activeColumn.expression.hasOwnProperty('ast')
	)
})
const showSimpleColumnEditor = computed(() => {
	if (activeColumnIdx.value === null) return false
	return !showExpressionEditor.value
})

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
	<div>
		<SectionHeader title="Summarize" :icon="Combine">
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
			:items="columns"
			group="columns"
			item-key="label"
			empty-text="No columns selected"
			@sort="onColumnSort"
		>
			<template #item="{ item: column, index: idx }">
				<Popover
					:show="showSimpleColumnEditor && activeColumnIdx === idx"
					@close="activeColumnIdx = null"
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

	<Dialog
		:modelValue="showExpressionEditor"
		@close="activeColumnIdx = null"
		:options="{
			title: 'Expression',
			size: '3xl',
			actions: [
				{ label: 'Discard', variant: 'outline', onClick: () => (activeColumnIdx = null) },
				{
					label: 'Save',
					variant: 'solid',
					onClick: () => onSaveColumn(columns[activeColumnIdx]),
				},
			],
		}"
	>
		<template #body-content>
			<ColumnExpressionEditor :column="columns[activeColumnIdx]" />
		</template>
	</Dialog>
</template>
