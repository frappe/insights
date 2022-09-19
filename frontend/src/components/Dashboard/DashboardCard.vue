<template>
	<div class="h-full w-full rounded-md bg-gray-50">
		<div
			v-if="show"
			class="group relative flex h-full w-full flex-col overflow-hidden rounded-md border border-gray-300 bg-white px-4 py-2"
		>
			<div
				v-if="!dashboard.editingLayout"
				class="invisible absolute top-2 right-2 flex h-5 items-center group-hover:visible"
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
</template>

<script setup>
import { computed, reactive, inject, provide } from 'vue'
import { useVisualization } from '@/utils/visualizations'
import { safeJSONParse } from '@/utils'

const emit = defineEmits(['edit', 'remove', 'layoutChange'])

const dashboard = inject('dashboard')
const props = defineProps({
	visualizationID: {
		type: String,
		required: true,
	},
	queryID: {
		type: String,
		required: true,
	},
})

const show = computed(() => {
	return visualization.type && visualization.component && visualization.componentProps
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
</script>
