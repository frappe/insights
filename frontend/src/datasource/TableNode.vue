<script setup>
import useDataSourceTable from '@/datasource/useDataSourceTable'
import { Handle, Position } from '@vue-flow/core'
import { inject } from 'vue'

const state = inject('state')
const props = defineProps({ tablename: { type: String, required: true } })
const table = await useDataSourceTable({ name: props.tablename })

function onColumnDragStart(event, column) {
	if (event.dataTransfer) {
		event.dataTransfer.setData('dragging-column', JSON.stringify(column))
		event.dataTransfer.effectAllowed = 'move'
	}
}
function onColumnDragOver(event) {
	event.preventDefault()
	if (event.dataTransfer) {
		event.dataTransfer.dropEffect = 'move'
	}
}
function onColumnDrop(event, column) {
	state.highlightColumn(null)

	event.preventDefault()
	event.stopPropagation()

	const data = event.dataTransfer?.getData('dragging-column')
	if (!data) return
	const fromColumn = JSON.parse(data)
	if (fromColumn.table === table.doc.table) return

	const toColumn = column
	state.createRelationship(fromColumn, toColumn)
}

function isHighlighted(column) {
	if (!state.highlightedColumn) return false
	return (
		state.highlightedColumn.table === column.table &&
		state.highlightedColumn.column === column.column
	)
}

function getTopOffset(idx) {
	return `${idx * 32 + 8}px`
}
</script>

<template>
	<div class="w-56 overflow-hidden rounded bg-white shadow">
		<div class="flex items-center border-b bg-gray-50 px-4 py-2">
			<span class="truncate font-medium">{{ table.doc.label }}</span>
		</div>
		<div class="nowheel flex max-h-72 flex-col overflow-y-scroll">
			<div
				v-for="(column, idx) in table.columns"
				:key="column.column"
				class="nodrag group relative flex cursor-pointer items-center justify-between border-b px-4 py-2 text-sm hover:bg-gray-50"
				:draggable="true"
				@dragover="onColumnDragOver"
				@dragstart="onColumnDragStart($event, column)"
				@drop="onColumnDrop($event, column)"
				@dragenter="state.highlightColumn(column)"
				:class="isHighlighted(column) ? 'bg-gray-100' : ''"
			>
				<div class="space-x-2">
					<span class="text-gray-500"> # </span>
					<span class="truncate">{{ column.label }}</span>
				</div>
				<Handle
					class="invisible"
					:id="column.column"
					type="source"
					:position="Position.Right"
					:style="{
						right: '0px',
						top: '15px',
					}"
				/>
				<Handle
					class="invisible"
					:id="column.column"
					type="target"
					:position="Position.Left"
					:style="{
						left: '0px',
						top: '15px',
					}"
				/>
			</div>
		</div>
	</div>
</template>
