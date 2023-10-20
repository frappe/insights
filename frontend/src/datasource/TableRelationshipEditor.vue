<script setup>
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { nextTick, watch } from 'vue'
import TableNode from './TableNode.vue'

const props = defineProps({
	tables: {
		type: Array,
		default: () => [],
	},
	relationships: {
		type: Array,
		default: () => [],
	},
})

const { nodes, edges, findNode, onConnect, addEdges, addNodes, project, vueFlowRef } = useVueFlow({
	nodes: [],
})
onConnect((params) => addEdges(params))

function onDragOver(event) {
	event.preventDefault()
	if (event.dataTransfer) {
		event.dataTransfer.dropEffect = 'move'
	}
}

async function onDrop(event) {
	const tablename = event.dataTransfer.getData('vueflow-drop-tablename')
	if (!tablename) {
		console.warn('no tablename found in drop event')
		return
	}
	if (findNode(tablename)) {
		console.warn('node already exists')
		return
	}

	const { left, top } = vueFlowRef.value.getBoundingClientRect()
	const position = project({
		x: event.clientX - left,
		y: event.clientY - top,
	})

	const newNode = {
		id: tablename,
		type: 'table',
		position,
	}
	addNodes([newNode])

	// align node position after drop, so it's centered to the mouse
	nextTick(() => {
		const node = findNode(newNode.id)
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

// onMounted(() => {
// 	const startX = 50
// 	const startY = 50
// 	const nodeWidth = 300
// 	const nodeHeight = 300
// 	const canvasWidth = 1000
// 	const canvasHeight = Infinity

// 	function calculatePosition(idx) {
// 		const x = startX + (idx % 4) * nodeWidth
// 		const y = startY + Math.floor(idx / 4) * nodeHeight
// 		return project({ x, y })
// 	}

// 	const initalNodes = props.tables.map((table, idx) => {
// 		return {
// 			id: table.name,
// 			position: calculatePosition(idx),
// 			type: 'table',
// 			data: {
// 				tablename: table.name,
// 				table_label: table.label,
// 				columns: table.columns,
// 			},
// 		}
// 	})
// 	addNodes(initalNodes)
// })
</script>

<template>
	<div class="h-full w-full" @drop="onDrop">
		<VueFlow @dragover="onDragOver">
			<template #node-table="{ id }">
				<Suspense>
					<TableNode :tablename="id" />
					<template #fallback>
						<div
							class="flex w-56 items-center justify-center overflow-hidden rounded bg-white py-8 shadow"
						>
							<LoadingIndicator class="h-6 w-6 text-gray-400" />
						</div>
					</template>
				</Suspense>
			</template>
		</VueFlow>
	</div>
</template>
