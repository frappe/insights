<script setup lang="ts">
import ColorInput from '@/components/Controls/ColorInput.vue'
import { debounce } from 'frappe-ui'
import { RefreshCcw, Settings, XIcon } from 'lucide-vue-next'
import Checkbox from '../../components/Checkbox.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { AxisChartConfig } from '../../types/chart.types'
import { MeasureOption } from './ChartConfigForm.vue'
import CollapsibleSection from './CollapsibleSection.vue'

const props = defineProps<{ measures: MeasureOption[] }>()
const y_axis = defineModel<AxisChartConfig['y_axis']>({
	required: true,
	default: () => ({
		series: [],
	}),
})

const emptySeries = { measure: {} as MeasureOption }
if (!y_axis.value?.series?.length) {
	y_axis.value = { series: [{ ...emptySeries }] }
}
function addSeries() {
	y_axis.value.series.push({ ...emptySeries })
}
function resetSeriesConfig(idx: number) {
	y_axis.value.series[idx] = {
		measure: y_axis.value.series[idx].measure,
	}
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
			<template v-for="(s, idx) in y_axis.series" :key="idx">
				<div class="flex items-end gap-1">
					<div class="flex-1">
						<Autocomplete
							:label="y_axis.series.length > 1 ? `Series ${idx + 1}` : 'Series'"
							placeholder="Select a column"
							:showFooter="true"
							:options="props.measures"
							:modelValue="s.measure.measure_name"
							@update:modelValue="s.measure = $event || {}"
						/>
					</div>
					<Popover v-if="s.measure.measure_name" placement="bottom-end">
						<template #target="{ togglePopover }">
							<Button @click="togglePopover">
								<template #icon>
									<Settings class="h-4 w-4 text-gray-700" stroke-width="1.5" />
								</template>
							</Button>
						</template>
						<template #body-main>
							<div class="flex w-[14rem] flex-col gap-2 p-2">
								<InlineFormControlLabel label="Label">
									<FormControl
										v-model="s.measure.measure_name"
										autocomplete="off"
										:debounce="500"
									/>
								</InlineFormControlLabel>
								<InlineFormControlLabel label="Type">
									<FormControl
										type="select"
										v-model="s.type"
										:options="['Line', 'Bar']"
									/>
								</InlineFormControlLabel>
								<InlineFormControlLabel label="Align">
									<FormControl
										type="select"
										v-model="s.align"
										:options="['Left', 'Right']"
									/>
								</InlineFormControlLabel>
								<InlineFormControlLabel label="Color">
									<ColorInput
										:model-value="s.color?.[0]"
										@update:model-value="updateColor($event, idx)"
										placement="left-start"
									/>
								</InlineFormControlLabel>
								<Checkbox label="Show Data Labels" v-model="s.show_data_labels" />

								<slot name="series-settings" :series="s" :idx="idx" />

								<div class="flex gap-1">
									<Button
										class="w-full"
										@click="resetSeriesConfig(idx)"
										variant="outline"
									>
										<template #prefix>
											<RefreshCcw
												class="h-4 w-4 text-gray-700"
												stroke-width="1.5"
											/>
										</template>
										Reset
									</Button>
									<Button
										class="w-full"
										@click="y_axis.series.splice(idx, 1)"
										variant="outline"
										theme="red"
									>
										<template #prefix>
											<XIcon
												class="h-4 w-4 text-red-700"
												stroke-width="1.5"
											/>
										</template>
										Remove
									</Button>
								</div>
							</div>
						</template>
					</Popover>
					<Button v-else class="flex-shrink-0" @click="y_axis.series.splice(idx, 1)">
						<template #icon>
							<XIcon class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
				</div>
			</template>
			<button
				class="-mt-1 text-left text-xs text-gray-600 hover:underline"
				@click="addSeries"
			>
				+ Add series
			</button>

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
