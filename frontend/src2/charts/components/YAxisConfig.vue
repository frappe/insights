<script setup lang="ts">
import ColorInput from '@/components/Controls/ColorInput.vue'
import { debounce } from 'frappe-ui'
import { watchEffect } from 'vue'
import Checkbox from '../../components/Checkbox.vue'
import DraggableList from '../../components/DraggableList.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { AxisChartConfig } from '../../types/chart.types'
import { MeasureOption } from './ChartConfigForm.vue'
import CollapsibleSection from './CollapsibleSection.vue'
import MeasurePicker from './MeasurePicker.vue'
import { copy } from '../../helpers'

const props = defineProps<{ measures: MeasureOption[] }>()
const y_axis = defineModel<AxisChartConfig['y_axis']>({
	required: true,
	default: () => ({
		series: [],
	}),
})

const emptySeries = { measure: {} as MeasureOption }
watchEffect(() => {
	if (!y_axis.value?.series?.length) {
		y_axis.value = { series: [copy(emptySeries)] }
	}
})

function addSeries() {
	y_axis.value.series.push(copy(emptySeries))
}

const updateColor = debounce((color: string, idx: number) => {
	if (!y_axis.value.series[idx].color) {
		y_axis.value.series[idx].color = []
	}
	y_axis.value.series[idx].color = color ? [color] : []
}, 500)
</script>

<template>
	<CollapsibleSection title="Y Axis">
		<div class="flex flex-col gap-3 pt-1">
			<div>
				<p class="mb-1.5 text-xs text-gray-600">Series</p>
				<div>
					<DraggableList v-model:items="y_axis.series" group="series">
						<template #item="{ item, index }">
							<MeasurePicker
								:options="props.measures"
								:model-value="item.measure"
								@update:model-value="Object.assign(item.measure, $event || {})"
								@remove="y_axis.series.splice(index, 1)"
							>
								<template #config-fields>
									<InlineFormControlLabel label="Type">
										<FormControl
											type="select"
											v-model="item.type"
											:options="['Line', 'Bar']"
										/>
									</InlineFormControlLabel>
									<InlineFormControlLabel label="Align">
										<FormControl
											type="select"
											v-model="item.align"
											:options="['Left', 'Right']"
										/>
									</InlineFormControlLabel>
									<InlineFormControlLabel label="Color">
										<ColorInput
											:model-value="item.color?.[0]"
											@update:model-value="updateColor($event, index)"
											placement="left-start"
										/>
									</InlineFormControlLabel>
									<Checkbox
										label="Show Data Labels"
										v-model="item.show_data_labels"
									/>

									<slot name="series-settings" :series="item" :idx="index" />
								</template>
							</MeasurePicker>
						</template>
					</DraggableList>
					<button
						class="mt-1.5 text-left text-xs text-gray-600 hover:underline"
						@click="addSeries"
					>
						+ Add series
					</button>
				</div>
			</div>

			<slot name="y-axis-settings" :y_axis="y_axis" />

			<Checkbox label="Show Data Labels" v-model="y_axis.show_data_labels" />
			<Checkbox label="Show Axis Label" v-model="y_axis.show_axis_label" />
			<FormControl
				v-if="y_axis.show_axis_label"
				v-model="y_axis.axis_label"
				label="Axis Label"
			/>
		</div>
	</CollapsibleSection>
</template>
