<template>
	<DraggableResizeable
		v-if="visualization.doc"
		:parentID="props.parentID"
		:targetID="visualization.doc.name"
		@move="onMove"
		@resize="onResize"
	>
		<div :id="visualization.doc.name" class="inline-block h-fit w-fit p-1" :style="style">
			<div
				class="flex h-full w-full flex-col overflow-hidden rounded-md border bg-white p-4 pt-3 shadow"
			>
				<div class="flex h-8 items-center justify-between">
					<div class="text-base font-medium">{{ visualization.doc.title }}</div>
					<div>
						<Button
							icon="settings"
							appearance="minimal"
							@mousedown.prevent.stop=""
							@click.prevent.stop="$emit('edit', props.queryID)"
						/>
						<Button
							icon="x"
							appearance="minimal"
							@mousedown.prevent.stop=""
							@click.prevent.stop="$emit('remove', props.visualizationID)"
						/>
					</div>
				</div>
				<div class="h-[calc(100%-2rem)]">
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
import { useVisualization } from '@/utils/visualization'
import { safeJSONParse } from '@/utils'

defineEmits(['edit', 'remove'])

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
})

const visualizationRow = dashboard.doc.visualizations.find(
	(row) => row.visualization === props.visualizationID
)
visualizationRow.layout = safeJSONParse(visualizationRow.layout, {})

const layout = reactive({
	top: visualizationRow.layout.top,
	left: visualizationRow.layout.left,
	width: visualizationRow.layout.width,
	height: visualizationRow.layout.height,
})
provide('layout', layout) // used by components to listen to resize events

const visualization = useVisualization({
	visualizationID: props.visualizationID,
	queryID: props.queryID,
})

const style = computed(() => {
	let style = ``
	if (layout.left) style += `left: ${layout.left}px;`
	if (layout.top) style += `top: ${layout.top}px;`

	if (layout.width) style += `width: ${layout.width}px;`
	if (layout.height) style += `height: ${layout.height}px;`
	return style
})

const onMove = ({ x, y }) => {
	layout.left = x
	layout.top = y
	updateLayout()
}
const onResize = ({ width, height }) => {
	layout.width = width
	layout.height = height
	updateLayout()
}
const updateLayout = () => {
	dashboard.updateVisualizationLayout.submit({
		visualization: props.visualizationID,
		layout: {
			left: layout.left,
			top: layout.top,
			width: layout.width,
			height: layout.height,
		},
	})
}
</script>
