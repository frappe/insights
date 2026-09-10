<script setup lang="ts">
import { debounce } from 'frappe-ui'
import { computed } from 'vue'
import ColorInput from '../../components/ColorInput.vue'
import DraggableList from '../../components/DraggableList.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { FIELDTYPES } from '../../helpers/constants'
import { DEFAULT_CHOICE, periodOf, periodOfChoice } from '../window'
import { NumberChartConfig, NumberColumnOptions } from '../../types/chart.types'
import { ColumnOption, Dimension, DimensionOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'
import NumberFormatFields from './NumberFormatFields.vue'
import NumberFormatSection from './NumberFormatSection.vue'
import NumberValueContext from './NumberValueContext.vue'
import NumberWindowPicker from './NumberWindowPicker.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
}>()

const config = defineModel<NumberChartConfig>({
	required: true,
	default: () => ({
		number_columns: [],
		number_column_options: [],
		sparkline: false,
	}),
})

const date_dimensions = computed(() =>
	props.dimensions.filter((d) => FIELDTYPES.DATE.includes(d.data_type)),
)

// What the card reads, which is what decides whether a period comparison is on
// offer and whether a sparkline has a series behind it.
const period = computed(() => periodOf(config.value))

const updateColor = debounce((color: string) => {
	config.value.sparkline_color = color
}, 500)

function getNumberOption(index: number, option: keyof NumberColumnOptions) {
	return config.value.number_column_options[index]?.[option]
}
function setNumberOption(index: number, option: keyof NumberColumnOptions, value: any) {
	if (!config.value.number_column_options[index]) {
		config.value.number_column_options[index] = {} as NumberColumnOptions
	}
	config.value.number_column_options[index][option] = value
}

/**
 * How good a fall is, moved onto the value.
 *
 * It is a per-value setting now. What a value is measured against is one too,
 * and `insights.patches.normalize_number_card_comparisons` moved that where it
 * belongs, so the only chart-level setting left to lower is this one.
 *
 * How a number prints is not here: `number_format` and `number_formats` sit over
 * the old spellings rather than replacing them, so nothing has to be rewritten.
 */
function lowerChartLevelSettings() {
	const chart = config.value
	// Nothing to move, so nothing is written. A form that rewrote the config on
	// open would mark every chart it was opened on dirty.
	if (!chart.negative_is_better) return

	chart.number_columns?.forEach((_, index) => {
		// A value that set something of its own already overrode the chart, so
		// lowering the chart's onto it would undo the override.
		chart.number_column_options[index] = {
			negative_is_better: chart.negative_is_better,
			...(chart.number_column_options[index] || {}),
		}
	})

	delete chart.negative_is_better
}

/**
 * The column and the period are one decision, so one handler answers both.
 *
 * A date column that groups nothing is a date column doing nothing, which is
 * why the picker offers no "None" — picking a column picks a period, and
 * dropping the column drops it. Written only on an author's action, never on
 * open, so no chart is dirtied by being looked at.
 */
function setDateColumn(dimension?: Dimension) {
	config.value.date_column = dimension || ({} as Dimension)

	if (!config.value.date_column?.column_name) {
		delete config.value.window
		return
	}
	if (!periodOf(config.value)) {
		config.value.window = periodOfChoice(DEFAULT_CHOICE)
	}
}

lowerChartLevelSettings()
</script>

<template>
	<CollapsibleSection title="Options">
		<div class="flex flex-col gap-3 pt-1">
			<div>
				<p class="mb-1.5 text-xs text-ink-gray-5">Columns</p>
				<div>
					<DraggableList v-model:items="config.number_columns" group="numbers">
						<template #item="{ item, index }">
							<MeasurePicker
								:model-value="item"
								:column-options="props.columnOptions"
								:enable-format="true"
								config-width="19rem"
								@update:model-value="Object.assign(item, $event || {})"
								@remove="config.number_columns.splice(index, 1)"
							>
								<template #config-fields="{ close: closeSettings }">
									<NumberFormatFields
										:config="config"
										:measure-name="item.measure_name"
									/>
									<InlineFormControlLabel label="Color">
										<ColorInput
											:model-value="getNumberOption(index, 'color') as string"
											@update:model-value="
												setNumberOption(index, 'color', $event)
											"
											placement="left-start"
										/>
									</InlineFormControlLabel>

									<Toggle
										label="Negative is better"
										:modelValue="getNumberOption(index, 'negative_is_better')"
										@update:modelValue="
											setNumberOption(index, 'negative_is_better', $event)
										"
									/>

									<div class="mt-1 border-t pt-2">
										<NumberValueContext
											:column-options="props.columnOptions"
											:period="period"
											:date-column="config.date_column as Dimension"
											:target="getNumberOption(index, 'target') as any"
											:comparison="
												getNumberOption(index, 'comparison') as any
											"
											@update:target="
												setNumberOption(index, 'target', $event)
											"
											@update:comparison="
												setNumberOption(index, 'comparison', $event)
											"
											@dialog-open="closeSettings"
										/>
									</div>
								</template>
							</MeasurePicker>
						</template>
					</DraggableList>
					<button
						class="mt-1.5 text-left text-xs text-ink-gray-5 hover:underline"
						@click="config.number_columns.push({} as any)"
					>
						+ Add column
					</button>
				</div>
			</div>
		</div>
	</CollapsibleSection>

	<CollapsibleSection title="Date">
		<div class="flex flex-col gap-3 pt-1">
			<DimensionPicker
				label="Column"
				:options="date_dimensions"
				:enable-granularity="false"
				:model-value="config.date_column as Dimension"
				@update:model-value="setDateColumn($event)"
			/>

			<NumberWindowPicker
				v-model="config.window"
				:has-date-column="Boolean(config.date_column?.column_name)"
			/>

			<!-- No period, no series: the card is one number, so a sparkline would
			     be one point. -->
			<Toggle v-if="period" label="Sparkline" v-model="config.sparkline" />

			<InlineFormControlLabel v-if="period && config.sparkline" label="Color">
				<ColorInput
					:model-value="config.sparkline_color"
					@update:model-value="updateColor($event)"
					placement="left-start"
				/>
			</InlineFormControlLabel>
		</div>
	</CollapsibleSection>

	<NumberFormatSection :config="config" />
</template>
