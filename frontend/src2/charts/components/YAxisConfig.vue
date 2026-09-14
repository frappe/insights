<script setup lang="ts">
import AddSlotButton from './AddSlotButton.vue'
import ColorInput from '../../components/ColorInput.vue'
import { debounce } from 'frappe-ui'
import DraggableList from '../../components/DraggableList.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import NumberInput from '../../components/NumberInput.vue'
import { copy } from '../../helpers'
import { AxisChartConfig, NumberFormatConfig } from '../../types/chart.types'
import { ColumnOption, MeasureOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import MeasurePicker from './MeasurePicker.vue'
import NumberFormatFields from './NumberFormatFields.vue'
import NumberFormatSection from './NumberFormatSection.vue'

// `config` is the whole Chart's, beside the axis: how a number prints is the
// Chart's to default and each Measure's to override, and the axis owns neither.
const props = defineProps<{ columnOptions: ColumnOption[]; config: NumberFormatConfig }>()
const y_axis = defineModel<AxisChartConfig['y_axis']>({
	required: true,
	default: () => ({
		series: [],
	}),
})

// The empty series a chart opens on is seeded on load, by `ensureConfigSlots`.
// Seeding it here would write the config on mount, which is one autosave and two
// re-runs of the chart data for opening a chart.
const emptySeries = { measure: {} as MeasureOption }

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
	<CollapsibleSection :title="__('Y Axis')">
		<div class="pt-1">
			<p class="mb-1.5 text-xs text-ink-gray-5">{{ __('Series') }}</p>
			<DraggableList v-model:items="y_axis.series" group="series">
				<template #item="{ item, index }">
					<MeasurePicker
						:model-value="item.measure"
						:column-options="props.columnOptions"
						@update:model-value="Object.assign(item.measure, $event || {})"
						@remove="y_axis.series.splice(index, 1)"
					>
						<template #config-fields>
							<NumberFormatFields
								:config="props.config"
								:measure-name="item.measure?.measure_name"
							/>
							<InlineFormControlLabel :label="__('Type')">
								<FormControl
									type="select"
									v-model="item.type"
									:options="[
										{ label: __('Line'), value: 'line' },
										{ label: __('Bar'), value: 'bar' },
									]"
								/>
							</InlineFormControlLabel>
							<InlineFormControlLabel :label="__('Align')">
								<FormControl
									type="select"
									v-model="item.align"
									:options="[
										{ label: __('Left'), value: 'Left' },
										{ label: __('Right'), value: 'Right' },
									]"
								/>
							</InlineFormControlLabel>
							<InlineFormControlLabel :label="__('Color')">
								<ColorInput
									:model-value="item.color?.[0]"
									@update:model-value="updateColor($event, index)"
									placement="left-start"
								/>
							</InlineFormControlLabel>
							<Toggle :label="__('Data labels')" v-model="item.show_data_labels" />
							<slot name="series-settings" :series="item" :idx="index" />
						</template>
					</MeasurePicker>
				</template>
			</DraggableList>
			<AddSlotButton :label="__('Add series')" @click="addSeries" />
		</div>
	</CollapsibleSection>

	<CollapsibleSection :title="__('Y Axis Options')" collapsed>
		<div class="flex flex-col gap-3 pt-1">
			<slot name="y-axis-settings" :y_axis="y_axis" />
			<Toggle :label="__('Data labels')" v-model="y_axis.show_data_labels" />
			<Toggle :label="__('Axis label')" v-model="y_axis.show_axis_label" />
			<InlineFormControlLabel v-if="y_axis.show_axis_label" :label="__('Text')">
				<FormControl v-model="y_axis.axis_label" />
			</InlineFormControlLabel>
			<InlineFormControlLabel :label="__('Y-Min')" control-width="5rem">
				<NumberInput v-model="y_axis.min" :placeholder="__('Min')" />
			</InlineFormControlLabel>
			<InlineFormControlLabel :label="__('Y-Max')" control-width="5rem">
				<NumberInput v-model="y_axis.max" :placeholder="__('Max')" />
			</InlineFormControlLabel>
		</div>
	</CollapsibleSection>

	<NumberFormatSection :config="props.config" />
</template>
