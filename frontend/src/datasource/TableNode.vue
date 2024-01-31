<script setup>
import useDataSourceTable from '@/datasource/useDataSourceTable'
import { fieldtypesToIcon } from '@/utils'
import { Handle, Position } from '@vue-flow/core'
import { inject, ref, watch } from 'vue'

const state = inject('state')
const edges = inject('edges')
const props = defineProps({ tablename: { type: String, required: true } })
const table = await useDataSourceTable({ name: props.tablename })

const columns = ref([...table.doc.columns])
watch(
	edges,
	() => {
		if (!edges.value?.length) return
		// based on the current edges, move the columns that are in the edges to the top
		const columnsInEdges = edges.value
			.filter(
				(edge) =>
					edge.data.primary_table === table.doc.table ||
					edge.data.foreign_table === table.doc.table
			)
			.map((edge) =>
				edge.data.primary_table === table.doc.table
					? edge.data.primary_column
					: edge.data.foreign_column
			)
		const newColumns = [...table.doc.columns]
		newColumns.sort((a, b) => {
			if (columnsInEdges.includes(a.column) && !columnsInEdges.includes(b.column)) return -1
			if (!columnsInEdges.includes(a.column) && columnsInEdges.includes(b.column)) return 1
			return 0
		})
		columns.value = newColumns
	},
	{ immediate: true }
)

function onColumnDragStart(event, column) {
	if (event.dataTransfer) {
		event.dataTransfer.setData(
			'dragging-column',
			JSON.stringify({
				table: table.doc.table,
				column: column.column,
				label: column.label,
				type: column.type,
			})
		)
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

	const toColumn = {
		table: table.doc.table,
		column: column.column,
		label: column.label,
		type: column.type,
	}
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
		<div class="nowheel flex max-h-72 flex-col overflow-y-auto">
			<div
				v-for="(column, idx) in columns"
				:key="column.column"
				class="nodrag group relative flex cursor-grab items-center border-b px-3 py-2 text-sm hover:bg-gray-50"
				:draggable="true"
				@dragover="onColumnDragOver"
				@dragstart="onColumnDragStart($event, column)"
				@drop="onColumnDrop($event, column)"
				@dragenter="state.highlightColumn(column)"
				:class="isHighlighted(column) ? 'bg-gray-100' : ''"
			>
				<component
					:is="fieldtypesToIcon[column.type]"
					class="mr-2 h-4 w-4 text-gray-500"
				></component>
				<span class="truncate">{{ column.label }}</span>
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
