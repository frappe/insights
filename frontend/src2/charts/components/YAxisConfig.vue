<script setup lang="ts">
import ColorInput from '../../components/ColorInput.vue'
import { debounce } from 'frappe-ui'
import { Settings, X as XIcon } from 'lucide-vue-next'
import { watchEffect } from 'vue'
import DraggableList from '../../components/DraggableList.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { copy } from '../../helpers'
import { AxisChartConfig, ReferenceLine } from '../../types/chart.types'
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

function addReferenceLine() {
	if (!y_axis.value.reference_lines) {
		y_axis.value.reference_lines = []
	}
	y_axis.value.reference_lines.push({ axis: 'y' } as ReferenceLine)
}

function removeReferenceLine(index: number) {
	y_axis.value.reference_lines?.splice(index, 1)
}
</script>

<template>
	<CollapsibleSection title="Y Axis">
		<div class="flex flex-col gap-3 pt-1">
			<div>
				<p class="mb-1.5 text-xs text-ink-gray-5">Series</p>
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
									<Toggle
										label="Hide from Chart"
										v-model="item.hide_from_chart"
									/>

									<slot name="series-settings" :series="item" :idx="index" />
								</template>
							</MeasurePicker>
						</template>
					</DraggableList>
					<button
						class="mt-1.5 text-left text-xs text-ink-gray-5 hover:underline"
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

			<div>
				<p class="mb-1.5 text-xs text-ink-gray-5">Reference Lines</p>
				<div class="flex flex-col gap-1.5">
					<div
						v-for="(line, index) in y_axis.reference_lines"
						:key="index"
						class="flex items-end gap-1"
					>
						<div class="flex-1 overflow-hidden">
							<FormControl
								type="text"
								v-model="line.value"
								:placeholder="
									line.axis === 'x' ? 'Value (e.g. Jan)' : 'Value (e.g. 60)'
								"
							/>
						</div>
						<Popover side="bottom" align="end">
							<template #trigger>
								<Button>
									<template #icon>
										<Settings
											class="h-4 w-4 text-ink-gray-6"
											stroke-width="1.5"
										/>
									</template>
								</Button>
							</template>
							<template #default>
								<div class="flex w-[14rem] flex-col gap-2 p-2">
									<InlineFormControlLabel label="Axis">
										<FormControl
											type="select"
											v-model="line.axis"
											:options="[
												{ label: 'Y (horizontal)', value: 'y' },
												{ label: 'X (vertical)', value: 'x' },
											]"
										/>
									</InlineFormControlLabel>
									<InlineFormControlLabel
										v-if="(line.axis || 'y') === 'y'"
										label="Align"
									>
										<FormControl
											type="select"
											v-model="line.align"
											:options="['Left', 'Right']"
										/>
									</InlineFormControlLabel>
									<InlineFormControlLabel label="Label">
										<FormControl
											type="text"
											v-model="line.label"
											placeholder="e.g. Target"
										/>
									</InlineFormControlLabel>
									<InlineFormControlLabel label="Color">
										<ColorInput
											:model-value="line.color"
											@update:model-value="line.color = $event"
											placement="left-start"
										/>
									</InlineFormControlLabel>
									<Toggle label="Dashed" v-model="line.dashed" />
								</div>
							</template>
						</Popover>
						<Button @click="removeReferenceLine(index)">
							<template #icon>
								<XIcon class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
							</template>
						</Button>
					</div>
				</div>
				<button
					class="mt-1.5 text-left text-xs text-ink-gray-5 hover:underline"
					@click="addReferenceLine"
				>
					+ Add reference line
				</button>
			</div>
		</div>
	</CollapsibleSection>
</template>
