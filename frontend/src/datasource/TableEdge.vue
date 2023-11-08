<script setup>
import { BaseEdge, EdgeLabelRenderer, getBezierPath, useVueFlow } from '@vue-flow/core'
import { computed, inject } from 'vue'

const props = defineProps({
	id: { type: String, required: true },
	sourceX: { type: Number, required: true },
	sourceY: { type: Number, required: true },
	targetX: { type: Number, required: true },
	targetY: { type: Number, required: true },
	sourcePosition: { type: String, required: true },
	targetPosition: { type: String, required: true },
	data: { type: Object, required: false },
	markerEnd: { type: String, required: false },
	style: { type: Object, required: false },
})

const state = inject('state')
const path = computed(() => getBezierPath(props))
const dropdownOptions = [
	{
		group: 'Cardinality',
		items: [
			{
				label: 'One to One',
				onClick: () => state.setCardinality(props.id, '1:1'),
			},
			{
				label: 'One to Many',
				onClick: () => state.setCardinality(props.id, '1:N'),
			},
			{
				label: 'Many to One',
				onClick: () => state.setCardinality(props.id, 'N:1'),
			},
			{
				label: 'Many to Many',
				onClick: () => state.setCardinality(props.id, 'N:N'),
			},
		],
	},
	{
		group: 'Actions',
		items: [
			{
				label: 'Delete',
				icon: 'trash',
				onClick: () => state.deleteRelationship(props.id),
			},
		],
	},
]
</script>

<script>
export default {
	inheritAttrs: false,
}
</script>

<template>
	<BaseEdge :id="id" :style="style" :path="path[0]" :marker-end="markerEnd" />
	<EdgeLabelRenderer>
		<div
			:style="{
				pointerEvents: 'all',
				position: 'absolute',
				transform: `translate(-50%, -50%) translate(${path[1]}px,${path[2]}px)`,
			}"
			class="nodrag nopan"
		>
			<Dropdown :options="dropdownOptions">
				<Button variant="outline">
					<span class="truncate font-mono"> {{ data.cardinality || '1:1' }} </span>
				</Button>
			</Dropdown>
		</div>
	</EdgeLabelRenderer>
</template>
