<template>
	<DraggableResizeable
		v-if="visualization.doc"
		:parentID="props.parentID"
		:targetID="visualization.doc.name"
		:enabled="dashboard.editingLayout"
		@move="onMove"
		@resize="onResize"
	>
		<div
			:id="visualization.doc.name"
			class="inline-block h-fit w-fit"
			:style="style"
			:class="{ 'cursor-grab': dashboard.editingLayout }"
		>
			<div
				class="relative flex h-full w-full flex-col overflow-hidden rounded-md border border-gray-300 bg-white px-4 py-2"
			>
				<div
					v-if="dashboard.editingLayout"
					class="absolute top-2 right-2 flex h-5 items-center"
				>
					<div class="cursor-pointer rounded p-1 text-gray-600 hover:bg-gray-100">
						<FeatherIcon
							name="external-link"
							class="h-3.5 w-3.5"
							@mousedown.prevent.stop=""
							@click.prevent.stop="$emit('edit', props.queryID)"
						/>
					</div>
					<div class="cursor-pointer rounded p-1 text-gray-600 hover:bg-gray-100">
						<FeatherIcon
							name="x"
							class="h-4 w-4"
							@mousedown.prevent.stop=""
							@click.prevent.stop="$emit('remove', props.visualizationID)"
						/>
					</div>
				</div>
				<div class="h-full">
					<component
						v-if="visualization.component && visualization.componentProps"
						:is="visualization.component"
						v-bind="visualization.componentProps"
					></component>
				</div>
			</div>
		</div>
	</DraggableResizeable>
</template>

<script setup>
import DraggableResizeable from '@/components/DraggableResizeable.vue'

import { computed, reactive, inject, provide } from 'vue'
import { useVisualization } from '@/utils/visualizations'
import { safeJSONParse } from '@/utils'

const emit = defineEmits(['edit', 'remove', 'layoutChange'])

const dashboard = inject('dashboard')
const props = defineProps({
	parentID: {
		type: String,
		required: true,
	},
	visualizationID: {
		type: String,
		required: true,
	},
	queryID: {
		type: String,
		required: true,
	},
	editing: {
		type: Boolean,
		default: false,
	},
})

const visualizationRow = dashboard.doc.visualizations.find(
	(row) => row.visualization === props.visualizationID
)
const initialLayout = safeJSONParse(visualizationRow.layout, {})

const layout = reactive({
	top: initialLayout.top,
	left: initialLayout.left,
	width: initialLayout.width,
	height: initialLayout.height,
})
provide('layout', layout) // used by components to listen to resize events

const visualization = useVisualization({
	visualizationID: props.visualizationID,
	queryID: props.queryID,
})

const style = computed(() => {
	let style = `position: absolute; `
	if (layout.left) style += `left: ${layout.left}px;`
	if (layout.top) style += `top: ${layout.top}px;`

	if (layout.width) style += `width: ${layout.width}px;`
	if (layout.height) style += `height: ${layout.height}px;`
	return style
})

const onMove = ({ x, y }) => {
	layout.left = x
	layout.top = y
	emit('layoutChange', props.visualizationID, layout)
}
const onResize = ({ width, height }) => {
	layout.width = width
	layout.height = height
	emit('layoutChange', props.visualizationID, layout)
}
</script>
