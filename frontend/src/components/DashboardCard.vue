<template>
	<DraggableResizeable
		v-if="visualization.doc"
		:parentID="props.parentID"
		:maintainAspectRatio="true"
		:targetID="visualization.doc.name"
		@move="onMove"
		@resize="onResize"
	>
		<div
			class="h-fit w-fit p-1"
			:id="visualization.doc.name"
			:data-x="layoutMeta.translateX"
			:data-y="layoutMeta.translateY"
			:style="style"
		>
			<div
				class="flex h-full w-full flex-col space-y-4 overflow-hidden rounded-md border bg-white p-4 shadow"
			>
				<div class="text-base font-medium">{{ visualization.doc.title }}</div>

				<div class="h-full w-full">
					<component
						v-if="visualization.component && visualization.componentProps"
						:is="visualization.component"
						v-bind="visualization.componentProps"
					></component>
					<!-- placeholder -->
					<div v-else class="h-full w-full">
						<div style="width: 600px; height: 300px"></div>
					</div>
				</div>
			</div>
		</div>
	</DraggableResizeable>
</template>

<script setup>
import DraggableResizeable from '@/components/DraggableResizeable.vue'

import { computed, reactive } from 'vue'
import { useVisualization } from '@/controllers/visualization'

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

const layoutMeta = reactive({
	width: 0,
	height: 0,
	translateX: 0,
	translateY: 0,
})

const visualization = useVisualization({
	visualizationID: props.visualizationID,
	queryID: props.queryID,
})

const style = computed(() => {
	let style = ``
	if (layoutMeta.width) {
		style += `width: ${layoutMeta.width}px;`
	}
	if (layoutMeta.height) {
		style += `height: ${layoutMeta.height}px;`
	}
	if (layoutMeta.translateX && layoutMeta.translateY) {
		style += `transform: translate(${layoutMeta.translateX}px, ${layoutMeta.translateY}px);`
	}
	return style
})

const onMove = ({ x, y }) => {
	layoutMeta.translateX = x
	layoutMeta.translateY = y
}
const onResize = ({ width, height }) => {
	layoutMeta.width = width
	layoutMeta.height = height
}
</script>
