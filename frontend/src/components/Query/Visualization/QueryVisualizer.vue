<template>
	<div class="flex h-full w-full flex-1 items-center pt-2">
		<div
			class="flex h-full w-72 flex-shrink-0 flex-col space-y-3 overflow-y-scroll border-r pr-4"
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
						v-for="(viz, i) in types"
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
				<ListPicker
					v-if="visualization.dataSchema.multipleValues"
					:value="
						Array.isArray(visualization.data.valueColumn)
							? visualization.data.valueColumn
							: visualization.data.valueColumn
							? [visualization.data.valueColumn]
							: undefined
					"
					:options="valueColumns"
					@selectOption="
						(options) => {
							visualization.data.valueColumn = options
						}
					"
				/>
				<Autocomplete
					v-else
					v-model="visualization.data.valueColumn"
					:options="valueColumns"
				/>
			</div>
			<div v-if="visualization.dataSchema.anyColumn" class="space-y-2 text-gray-600">
				<div class="text-base font-light text-gray-500">Select Columns</div>
				<ListPicker
					v-if="visualization.dataSchema.multiple"
					:value="visualization.data.columns ? visualization.data.columns : undefined"
					:options="allColumns"
					@selectOption="
						(options) => {
							visualization.data.columns = options
						}
					"
				/>
			</div>
			<div v-if="visualization.dataSchema.pivotColumn" class="space-y-2 text-gray-600">
				<div class="text-base font-light text-gray-500">Select Column</div>
				<Autocomplete v-model="visualization.data.pivotColumn" :options="pivotColumns" />
			</div>
			<div v-if="visualization.type == 'Line'" class="space-y-2 text-gray-600">
				<div class="text-base font-light text-gray-500">Line Curveness</div>
				<div class="flex w-full items-center">
					<input
						type="range"
						min="0"
						max="1"
						step="0.1"
						v-model="visualization.data.lineSmoothness"
						class="flex-1 focus:outline-none"
					/>
					<span class="ml-2 text-sm">{{ visualization.data.lineSmoothness }}</span>
				</div>
			</div>
			<Button
				appearance="primary"
				@click="saveVisualization"
				:loading="visualization.savingDoc"
			>
				Save Changes
			</Button>
		</div>
		<div class="flex h-[70%] w-[calc(100%-18rem)] pl-4">
			<component
				v-if="visualization.component && visualization.componentProps"
				:is="visualization.component"
				v-bind="visualization.componentProps"
			></component>
		</div>
	</div>
</template>

<script setup>
import ListPicker from '@/components/Controls/ListPicker.vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'

import { FIELDTYPES } from '@/utils'
import { computed, inject } from 'vue'
import { useVisualization, types } from '@/utils/visualizations'

const query = inject('query')
const visualizationID = query.visualizations[0]
const visualization = useVisualization({ visualizationID, query })

const invalidVizTypes = computed(() => {
	// TODO: change based on data
	return ['Funnel', 'Row']
})
const setVizType = (type) => {
	if (!invalidVizTypes.value.includes(type)) {
		visualization.setType(type)
	}
}

const allColumns = computed(() => {
	return query.doc.columns.map((c) => {
		return {
			label: c.label,
			value: c.column || c.label,
		}
	})
})

const labelColumns = computed(() => {
	return query.doc.columns
		.filter((c) => !FIELDTYPES.NUMBER.includes(c.type))
		.map((c) => {
			return {
				label: c.label,
				value: c.column || c.label,
			}
		})
})
const valueColumns = computed(() => {
	return query.doc.columns
		.filter((c) => FIELDTYPES.NUMBER.includes(c.type))
		.map((c) => {
			return {
				label: c.label,
				value: c.column || c.label,
			}
		})
})

const pivotColumns = computed(() => {
	return query.doc.columns
		.filter((c) => c.aggregation == 'Group By')
		.map((c) => {
			return {
				label: c.label,
				value: c.column || c.label,
			}
		})
})

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
