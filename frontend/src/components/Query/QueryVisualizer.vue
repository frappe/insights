<template>
	<div class="flex h-full min-h-[12rem] w-full flex-1 px-1 pt-4">
		<div
			class="flex h-full w-64 flex-shrink-0 flex-col space-y-3 overflow-y-scroll border-r pr-4"
		>
			<div class="space-y-2 text-gray-600">
				<div class="text-base font-light text-gray-500">Title</div>
				<Input
					type="text"
					placeholder="Enter a suitable title..."
					v-model="visualization.title"
				/>
			</div>
			<div class="space-y-2">
				<div class="text-base font-light text-gray-500">Select Visualization Type</div>
				<div class="-ml-1 grid grid-cols-[repeat(auto-fill,3.5rem)] gap-3">
					<div
						class="flex flex-col items-center space-y-1 text-gray-500"
						:class="{
							'cursor-pointer hover:text-gray-600': !invalidVizTypes.includes(
								viz.type
							),
							'cursor-not-allowed hover:text-gray-500': invalidVizTypes.includes(
								viz.type
							),
						}"
						v-for="(viz, i) in visualizations"
						:key="i"
						@click="setVizType(viz.type)"
					>
						<div
							class="flex h-12 w-12 items-center justify-center rounded-md border border-gray-200 bg-white hover:shadow"
							:class="{
								' border-blue-300 text-blue-500 shadow-sm hover:shadow-sm':
									viz.type == visualization.type,
								' border-dashed border-gray-300 opacity-60 hover:shadow-none':
									invalidVizTypes.includes(viz.type),
							}"
						>
							<FeatherIcon :name="viz.icon" class="h-6 w-6" />
						</div>
						<span
							class="text-sm"
							:class="{
								'font-normal text-blue-600': viz.type == visualization.type,
								'font-light': viz.type != visualization.type,
								'opacity-60': invalidVizTypes.includes(viz.type),
							}"
						>
							{{ viz.type }}
						</span>
					</div>
				</div>
			</div>
			<!-- Visualization Data Fields -->
			<div v-if="visualization.dataSchema.labelColumn" class="space-y-2 text-gray-600">
				<div class="text-base font-light text-gray-500">Select Dimension</div>
				<Autocomplete v-model="visualization.data.labelColumn" :options="labelColumns" />
			</div>
			<div v-if="visualization.dataSchema.valueColumn" class="space-y-2 text-gray-600">
				<div class="text-base font-light text-gray-500">Select Measure</div>
				<Autocomplete v-model="visualization.data.valueColumn" :options="valueColumns" />
			</div>
			<div v-if="visualization.dataSchema.pivotColumn" class="space-y-2 text-gray-600">
				<div class="text-base font-light text-gray-500">Select Column</div>
				<Autocomplete v-model="visualization.data.pivotColumn" :options="labelColumns" />
			</div>
			<button
				class="w-full rounded-md bg-gray-100 py-1.5 text-lg text-gray-500"
				:class="{
					'cursor-pointer bg-blue-500 text-white hover:bg-blue-600': !saveDisabled,
				}"
				@click="saveVisualization"
			>
				Save Changes
			</button>
		</div>
		<div class="flex w-[calc(100%-16rem)] pl-4">
			<component
				v-if="visualization.componentProps"
				:is="visualization.component"
				v-bind="visualization.componentProps"
			></component>
		</div>
	</div>
</template>

<script setup>
import Autocomplete from '@/components/Autocomplete.vue'

import { computed, inject, markRaw, reactive, watch } from 'vue'
import {
	visualizations,
	getVisualization,
	getVisualizationDoc,
	createVisualizationDoc,
	updateVisualizationDoc,
} from '@/controllers/visualization'

const query = inject('query')
const visualization = reactive({
	doc: null,
	type: '',
	data: {},
	dataSchema: {},
	component: null,
	controller: null,
	componentProps: null,
	query: query.doc.name,
	title: query.doc.title,
})

const queryName = computed(() => query.doc.name)
const fetchVisualizationDoc = (queryName) => {
	getVisualizationDoc({
		queryName,
		onSuccess: (doc) => {
			if (doc) {
				doc.data = JSON.parse(doc.data)

				visualization.doc = doc
				visualization.type = doc.type
				visualization.data = doc.data
				visualization.title = doc.title
			}
		},
	})
}
watch(queryName, fetchVisualizationDoc, { immediate: true })

const onTypeChange = (type) => {
	if (!type) {
		visualization.dataSchema = {}
		visualization.component = null
		visualization.componentProps = null
		return
	}

	if (!visualization.controller || visualization.controller.type != type) {
		visualization.controller = getVisualization(type)
	}

	visualization.dataSchema = visualization.controller.getDataSchema()
	// dynamic components shouldn't be reactive
	visualization.component = markRaw(visualization.controller.getComponent())
}
watch(() => visualization.type, onTypeChange)

const onDataChange = (data) => {
	if (visualization.type == 'Pivot' && data.pivotColumn) {
		applyPivotTransform(data.pivotColumn)
		return
	}
	visualization.componentProps = visualization.controller?.getComponentProps(query, data)
}
watch(() => visualization.data, onDataChange, { deep: true })

const applyPivotTransform = (pivotColumn) => {
	query.applyTransform({
		type: 'Pivot',
		data: {
			index_columns: labelColumns.value
				.filter((c) => c.label !== pivotColumn.label)
				.map((c) => c.label),
			pivot_columns: [pivotColumn.label],
		},
	})
}
watch(
	() => query.doc.transform_result,
	(transformResult) => {
		if (transformResult) {
			visualization.componentProps = {
				tableHtml: transformResult,
			}
		}
	},
	{ immediate: true }
)

const invalidVizTypes = computed(() => {
	// TODO: change based on data
	return ['Funnel', 'Row']
})
const setVizType = (type) => {
	if (invalidVizTypes.value.includes(type)) {
		return
	}
	visualization.type = type
	visualization.data = {}
}

const saveDisabled = computed(() => {
	// TODO: fix this

	// const { title, type, data } = visualization

	// const validLocalChart = title && type && data
	// const localAndRemoteChartMatches =
	// 	visualization.doc &&
	// 	visualization.doc.title == title &&
	// 	visualization.doc.type == type &&
	// 	JSON.stringify(visualization.doc.data) == JSON.stringify(data)

	// console.log(visualization.doc.data, data)

	// return (!visualization.doc && !validLocalChart) || localAndRemoteChartMatches
	return false
})

const labelColumns = computed(() => {
	return query.columns
		.filter((c) => c.aggregation == 'Group By')
		.map((c) => {
			return {
				label: c.label,
				value: c.value,
			}
		})
})
const valueColumns = computed(() => {
	return query.columns
		.filter((c) => c.aggregation != 'Group By')
		.map((c) => {
			return {
				label: c.label,
				value: c.value,
			}
		})
})

const $notify = inject('$notify')
const saveVisualization = () => {
	const { query: queryName, title, type, data } = visualization
	const onSuccess = () => {
		fetchVisualizationDoc(queryName)
		$notify({
			title: 'Visualization Saved',
			appearance: 'success',
		})
	}

	if (visualization.doc.name) {
		const docname = visualization.doc.name
		updateVisualizationDoc({ docname, title, type, data, onSuccess })
	} else {
		createVisualizationDoc({ queryName, title, type, data, onSuccess })
	}
}
</script>
