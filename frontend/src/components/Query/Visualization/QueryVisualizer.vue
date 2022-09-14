<template>
	<div class="flex h-full items-center pt-2">
		<div class="flex h-full w-[20rem] flex-col pr-4">
			<div class="mb-3">
				<div class="mb-2 text-sm tracking-wide text-gray-600">CHART TYPE</div>
				<ChartSelector
					v-if="types?.length > 0"
					:chartTypes="types"
					:invalidTypes="invalidTypes"
					:currentType="visualization.type"
					@chartTypeChange="setVizType"
				/>
			</div>

			<div class="flex-1 space-y-3 overflow-y-scroll">
				<div class="mb-2 text-sm tracking-wide text-gray-600">CHART OPTIONS</div>
				<ChartOptions :chartType="visualization.type" />
				<Button
					appearance="primary"
					@click="saveVisualization"
					:loading="visualization.savingDoc"
					:disabled="!visualization.isDirty"
				>
					Save Changes
				</Button>
			</div>
		</div>
		<div class="flex h-2/3 w-[calc(100%-20rem)] pl-4">
			<component
				v-if="visualization.component && visualization.componentProps"
				:is="visualization.component"
				v-bind="visualization.componentProps"
			></component>
		</div>
	</div>
</template>

<script setup>
import ChartSelector from '@/components/Query/Visualization/ChartSelector.vue'
import ChartOptions from '@/components/Query/Visualization/ChartOptions.vue'

import { computed, inject, provide } from 'vue'
import { useVisualization, types } from '@/utils/visualizations'

const query = inject('query')
const visualizationID = query.visualizations[0]
const visualization = useVisualization({ visualizationID, query })
provide('visualization', visualization)

const invalidTypes = computed(() => {
	// TODO: change based on data
	return ['Funnel', 'Row']
})
const setVizType = (type) => {
	if (!invalidTypes.value.includes(type)) {
		visualization.setType(type)
	}
}

const $notify = inject('$notify')
const saveVisualization = () => {
	const onSuccess = () => {
		$notify({
			title: 'Visualization Saved',
			appearance: 'success',
		})
	}
	visualization.updateDoc({ onSuccess })
}
</script>
