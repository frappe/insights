<script setup lang="ts">
import ColorInput from '@/components/Controls/ColorInput.vue'
import { debounce } from 'frappe-ui'
import { watchEffect } from 'vue'
import Checkbox from '../../components/Checkbox.vue'
import DraggableList from '../../components/DraggableList.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { copy } from '../../helpers'
import { AxisChartConfig } from '../../types/chart.types'
import { ColumnOption, MeasureOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import MeasurePicker from './MeasurePicker.vue'

const props = defineProps<{ columnOptions: ColumnOption[] }>()
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
								:model-value="item.measure"
								:column-options="props.columnOptions"
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
									<Toggle
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
			<Toggle label="Show Data Labels" v-model="y_axis.show_data_labels" />
			<Toggle label="Show Axis Label" v-model="y_axis.show_axis_label" />
			<Toggle label="Show Scrollbar" v-model="y_axis.show_scrollbar" />
			<FormControl
				v-if="y_axis.show_axis_label"
				v-model="y_axis.axis_label"
				label="Axis Label"
			/>

			<InlineFormControlLabel label="Y-Min" class="w-1/2">
				<FormControl type="number" v-model="y_axis.min" placeholder="Min" />
			</InlineFormControlLabel>
			<InlineFormControlLabel label="Y-Max" class="w-1/2">
				<FormControl type="number" v-model="y_axis.max" placeholder="Max" />
			</InlineFormControlLabel>
		</div>
	</CollapsibleSection>
</template>
