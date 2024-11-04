<script setup lang="ts">
import ColorInput from '@/components/Controls/ColorInput.vue'
import { debounce } from 'frappe-ui'
import { Edit, RefreshCcw, Settings, XIcon } from 'lucide-vue-next'
import { inject, ref, watchEffect } from 'vue'
import Checkbox from '../../components/Checkbox.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { AxisChartConfig } from '../../types/chart.types'
import { ExpressionMeasure, aggregations } from '../../types/query.types'
import { Chart } from '../chart'
import { MeasureOption } from './ChartConfigForm.vue'
import CollapsibleSection from './CollapsibleSection.vue'
import NewMeasureSelectorDialog from './NewMeasureSelectorDialog.vue'

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
		y_axis.value = { series: [{ ...emptySeries }] }
	}
})

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

const chart = inject<Chart>('chart')!
const showMeasureDialog = ref(false)
const currentMeasure = ref<ExpressionMeasure>()
function editMeasure(measure: ExpressionMeasure) {
	currentMeasure.value = measure
	showMeasureDialog.value = true
}
function updateMeasure(measure: ExpressionMeasure) {
	chart.updateMeasure(measure)
	if (currentMeasure.value) {
		const currentMeasureName = currentMeasure.value.measure_name
		if (currentMeasureName !== measure.measure_name) {
			chart.removeMeasure(currentMeasure.value)
		}
		y_axis.value.series.forEach((s) => {
			if (s.measure.measure_name === currentMeasureName) {
				s.measure = measure
			}
		})
		currentMeasure.value = undefined
	} else {
		const idx = y_axis.value.series.findIndex((s) => !s.measure.measure_name)
		if (idx > -1) {
			y_axis.value.series[idx].measure = measure
		} else {
			y_axis.value.series.push({ measure })
		}
	}
}
</script>

<template>
	<CollapsibleSection title="Y Axis">
		<div class="flex flex-col gap-3 pt-1">
			<template v-for="(s, idx) in y_axis.series" :key="s.measure.measure_name">
				<div class="flex items-end gap-1">
					<div class="flex-1">
						<Autocomplete
							:label="y_axis.series.length > 1 ? `Series ${idx + 1}` : 'Series'"
							placeholder="Select a column"
							:showFooter="true"
							:options="props.measures"
							:modelValue="s.measure.measure_name"
							@update:modelValue="s.measure = $event || {}"
						>
							<template #footer="{ togglePopover }">
								<div class="flex items-center justify-between">
									<Button
										label="Create New"
										@click="
											() => {
												showMeasureDialog = true
												togglePopover()
											}
										"
									/>
									<Button label="Clear" @click.stop="s.measure = {}" />
								</div>
							</template>
						</Autocomplete>
					</div>
					<Popover v-if="s.measure.measure_name" placement="bottom-end">
						<template #target="{ togglePopover }">
							<Button @click="togglePopover">
								<template #icon>
									<Settings class="h-4 w-4 text-gray-700" stroke-width="1.5" />
								</template>
							</Button>
						</template>
						<template #body-main="{ togglePopover }">
							<div class="flex w-[14rem] flex-col gap-2 p-2">
								<InlineFormControlLabel
									v-if="
										'aggregation' in s.measure &&
										s.measure.aggregation &&
										s.measure.column_name != 'count'
									"
									label="Function"
								>
									<Autocomplete
										button-classes="rounded-r-none"
										placeholder="Agg"
										:options="aggregations"
										:modelValue="s.measure.aggregation"
										@update:modelValue="s.measure.aggregation = $event.value"
										:hide-search="true"
									/>
								</InlineFormControlLabel>
								<Button
									v-if="
										'expression' in s.measure && s.measure.expression.expression
									"
									class="w-full"
									label="Edit Expression"
									@click="
										() => {
											editMeasure(s.measure as ExpressionMeasure)
											togglePopover()
										}
									"
								>
									<template #prefix>
										<Edit class="h-4 w-4 text-gray-700" stroke-width="1.5" />
									</template>
								</Button>
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

	<NewMeasureSelectorDialog
		v-if="showMeasureDialog"
		v-model="showMeasureDialog"
		:column-options="chart.baseQuery.result.columnOptions"
		:measure="currentMeasure"
		@select="updateMeasure"
	/>
</template>
