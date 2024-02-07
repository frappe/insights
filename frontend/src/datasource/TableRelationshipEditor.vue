<script setup>
import { whenHasValue } from '@/utils'
import { MarkerType, VueFlow, useVueFlow } from '@vue-flow/core'
import { useStorage, watchDebounced } from '@vueuse/core'
import { Grip } from 'lucide-vue-next'
import { computed, inject, nextTick, provide, reactive, ref, watch } from 'vue'
import TableEdge from './TableEdge.vue'
import TableNode from './TableNode.vue'
import useDataSourceTable from './useDataSourceTable'

const dataSource = inject('dataSource')
const searchQuery = ref('')
const filteredList = computed(() => {
	if (!searchQuery.value) {
		return dataSource.tableList.filter((table) => !table.is_query_based).slice(0, 100)
	}
	return dataSource.tableList
		.filter(
			(table) =>
				!table.is_query_based &&
				table.label.toLowerCase().includes(searchQuery.value.toLowerCase())
		)
		.slice(0, 100)
})

const state = reactive({
	highlightedColumn: null,
	highlightColumn(column) {
		state.highlightedColumn = column
	},
	createRelationship(fromColumn, toColumn) {
		if (!fromColumn.table || !fromColumn.column || !toColumn.table || !toColumn.column) {
			console.warn('Invalid relationship')
			return
		}
		const newEdge = {
			id: `${fromColumn.table}.${fromColumn.column} -> ${toColumn.table}.${toColumn.column}`,
			source: fromColumn.table,
			target: toColumn.table,
			sourceHandle: fromColumn.column,
			targetHandle: toColumn.column,
			type: 'custom',
			data: {
				primary_table: fromColumn.table,
				primary_column: fromColumn.column,
				foreign_table: toColumn.table,
				foreign_column: toColumn.column,
				cardinality: '1:1',
			},
			markerEnd: MarkerType.ArrowClosed,
		}
		canvas.addEdges([newEdge])
		dataSource.updateTableRelationship(newEdge.data)
	},
	setCardinality(id, cardinality) {
		const edge = canvas.findEdge(id)
		if (!edge) return
		edge.data.cardinality = cardinality
		dataSource.updateTableRelationship(edge.data)
	},
	deleteRelationship(id) {
		const edge = canvas.findEdge(id)
		dataSource.deleteTableRelationship(edge.data)
		canvas.removeEdges([id])
	},
})

provide('state', state)

const canvas = useVueFlow({ nodes: [] })

const storedNodes = useStorage(
	`insights:${dataSource.doc.name}:${dataSource.doc.creation}:nodes`,
	[]
)
const nodes = computed(() => canvas.nodes.value)
const edges = computed(() => canvas.edges.value)
provide('edges', edges)

// load locally stored nodes
if (storedNodes.value.length) {
	canvas.addNodes(storedNodes.value)
	const promises = storedNodes.value.map((node) => {
		if (node.type == 'table') {
			return displayTableRelationships(node.data.tablename)
		}
		return Promise.resolve()
	})
	await Promise.all(promises)
}

// when nodes change, store them locally
watchDebounced(
	nodes,
	(newNodes) => {
		if (JSON.stringify(newNodes) == JSON.stringify(storedNodes.value)) return
		storedNodes.value = newNodes
	},
	{ deep: true, debounce: 1000 }
)

function onTableDragStart(event, table) {
	if (event.dataTransfer) {
		event.dataTransfer.setData('dragging-table', JSON.stringify(table))
		event.dataTransfer.effectAllowed = 'move'
	}
}

function onTableDragOver(event) {
	event.preventDefault()
	if (event.dataTransfer) {
		event.dataTransfer.dropEffect = 'move'
	}
}

const $notify = inject('$notify')
async function onTableDrop(event) {
	event.preventDefault()

	const table = JSON.parse(event.dataTransfer?.getData('dragging-table'))
	if (!table) return
	if (canvas.findNode(table.table)) {
		$notify({ title: 'Table already added', variant: 'warning' })
		return
	}

	const { left, top } = canvas.vueFlowRef.value.getBoundingClientRect()
	const newNode = {
		id: table.table,
		type: 'table',
		data: { tablename: table.name },
		position: canvas.project({
			x: event.clientX - left,
			y: event.clientY - top,
		}),
	}
	canvas.addNodes([newNode])
	displayTableRelationships(table.name)

	// align node position after drop, so it's centered to the mouse
	nextTick(() => {
		const node = canvas.findNode(newNode.id)
		const stop = watch(
			() => node.dimensions,
			(dimensions) => {
				if (dimensions.width > 0 && dimensions.height > 0) {
					node.position = {
						x: node.position.x - node.dimensions.width / 2,
						y: node.position.y - node.dimensions.height / 2,
					}
					stop()
				}
			},
			{ deep: true, flush: 'post' }
		)
	})
}

async function displayTableRelationships(tablename) {
	const table = await useDataSourceTable({ name: tablename })
	await whenHasValue(() => table.doc.name)
	if (!table.doc.table_links) return
	table.doc.table_links.forEach((link) => {
		const foreignTableNode = canvas.findNode(link.foreign_table)
		if (!foreignTableNode) return
		const edgeData = {
			primary_table: table.doc.table,
			primary_column: link.primary_key,
			foreign_table: link.foreign_table,
			foreign_column: link.foreign_key,
			cardinality: link.cardinality,
		}
		const newEdge = {
			id: `${table.doc.table}.${link.primary_key} -> ${link.foreign_table}.${link.foreign_key}`,
			source: table.doc.table,
			target: link.foreign_table,
			sourceHandle: link.primary_key,
			targetHandle: link.foreign_key,
			type: 'custom',
			data: edgeData,
			markerEnd: MarkerType.ArrowClosed,
		}
		if (!canvas.findEdge(newEdge.id)) {
			canvas.addEdges([newEdge])
		}
	})
}

function calculatePosition(idx) {
	const startX = 50
	const startY = 50
	const nodeWidth = 300
	const nodeHeight = 300
	const canvasWidth = 1000
	const canvasHeight = Infinity

	const x = startX + (idx % 4) * nodeWidth
	const y = startY + Math.floor(idx / 4) * nodeHeight
	return canvas.project({ x, y })
}

function onEdgeChange(args) {
	if (!args?.[0]) return
	if (args[0].type == 'remove') {
		const [from, to] = args[0].id.split(' -> ')
		const [fromTable, fromColumn] = from.split('.')
		const [toTable, toColumn] = to.split('.')
		dataSource.deleteTableRelationship({
			primary_table: fromTable,
			primary_column: fromColumn,
			foreign_table: toTable,
			foreign_column: toColumn,
		})
	}
}
</script>

<template>
	<div class="relative flex flex-1 items-center justify-center bg-gray-50" @drop="onTableDrop">
		<VueFlow @dragover="onTableDragOver" @edges-change="onEdgeChange">
			<template #node-table="{ data }">
				<Suspense>
					<TableNode :tablename="data.tablename" />
					<template #fallback>
						<div
							class="flex w-56 items-center justify-center overflow-hidden rounded bg-white py-8 shadow"
						>
							<LoadingIndicator class="h-6 w-6 text-gray-400" />
						</div>
					</template>
				</Suspense>
			</template>
			<template #edge-custom="props">
				<TableEdge v-bind="props" />
			</template>
		</VueFlow>
		<div
			v-if="!nodes.length"
			class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 transform text-center text-gray-700"
		>
			Drag and drop tables from the left panel to create relationships.
		</div>
	</div>

	<div class="flex w-[21rem] flex-shrink-0 flex-col gap-3 overflow-hidden bg-white p-4 shadow">
		<div class="flex items-center justify-between">
			<div class="text-xl font-medium">Tables</div>
		</div>
		<Input placeholder="Search" icon-left="search" v-model="searchQuery" />
		<div class="flex-1 overflow-hidden">
			<div
				v-if="filteredList.length"
				class="flex h-full flex-col gap-2 overflow-y-auto overflow-x-hidden overflow-y-hidden"
			>
				<div
					v-for="table in filteredList"
					:key="table.name"
					class="group -mx-1 flex cursor-pointer items-center justify-between rounded-md px-2 py-1 hover:bg-gray-100"
					:draggable="true"
					@dragstart="onTableDragStart($event, table)"
				>
					<div class="flex items-center space-x-2 py-1">
						<Grip class="h-4 w-4 rotate-90 text-gray-600" />
						<span> {{ table.label }} </span>
					</div>
				</div>
			</div>
			<div v-if="!filteredList.length" class="flex h-full items-center justify-center">
				<div class="text-center text-gray-600">
					No tables.
					<div class="mt-1 text-base text-gray-700">No tables to display.</div>
				</div>
			</div>
		</div>
	</div>
</template>
