<script setup lang="ts">
import { debounce } from 'frappe-ui'
import { computed } from 'vue'
import ColorInput from '../../components/ColorInput.vue'
import DraggableList from '../../components/DraggableList.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { FIELDTYPES } from '../../helpers/constants'
import { measuredAgainst } from '../adapter/number'
import { NumberChartConfig, NumberColumnOptions } from '../../types/chart.types'
import { ColumnOption, Dimension, DimensionOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'
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
 * The settings an older release wrote, moved onto each value.
 *
 * Every one of them is a per-value setting now — the chart-level formatting
 * slots, the `comparison` flag, and the `references` list a value carried
 * before it named one target and one comparison. The adapter still reads all of
 * them so a chart nobody opens keeps drawing. But a form that hid a prefix it
 * was still printing would trap the author, so opening the chart is what moves
 * it: one shape from here on, and what the form shows is what draws.
 */
function lowerChartLevelSettings() {
	const chart = config.value
	const inherited: NumberColumnOptions = {}
	if (chart.prefix) inherited.prefix = chart.prefix
	if (chart.suffix) inherited.suffix = chart.suffix
	if (chart.decimal !== undefined) inherited.decimal = chart.decimal
	if (chart.shorten_numbers) inherited.shorten_numbers = chart.shorten_numbers
	if (chart.negative_is_better) inherited.negative_is_better = chart.negative_is_better

	const references = chart.number_column_options?.some(
		(options) => (options as { references?: unknown })?.references,
	)

	// Nothing to move, so nothing is written. A form that rewrote the config on
	// open would mark every chart it was opened on dirty.
	if (!Object.keys(inherited).length && !chart.comparison && !references) return

	chart.number_columns?.forEach((_, index) => {
		const options = chart.number_column_options[index] || {}
		// What the value is measured against, read the same way the adapter reads
		// it, so the form shows what the card is already drawing.
		const { target, comparison } = measuredAgainst(chart, options)
		delete (options as { references?: unknown }).references
		// A value that set something of its own already overrode the chart, so
		// lowering the chart's onto it would undo the override.
		chart.number_column_options[index] = {
			...inherited,
			...options,
			...(target ? { target } : {}),
			...(comparison ? { comparison } : {}),
		}
	})

	delete chart.prefix
	delete chart.suffix
	delete chart.decimal
	delete chart.shorten_numbers
	delete chart.negative_is_better
	delete chart.comparison
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
									<InlineFormControlLabel label="Units">
										<div class="grid grid-cols-3 gap-1">
											<FormControl
												autocomplete="off"
												placeholder="$"
												:modelValue="getNumberOption(index, 'prefix')"
												@update:modelValue="
													setNumberOption(index, 'prefix', $event)
												"
											/>
											<FormControl
												autocomplete="off"
												placeholder="unit"
												:modelValue="getNumberOption(index, 'suffix')"
												@update:modelValue="
													setNumberOption(index, 'suffix', $event)
												"
											/>
											<FormControl
												autocomplete="off"
												placeholder="0.0"
												type="number"
												:modelValue="getNumberOption(index, 'decimal')"
												@update:modelValue="
													setNumberOption(index, 'decimal', $event)
												"
											/>
										</div>
									</InlineFormControlLabel>
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
										label="Show short numbers"
										:modelValue="getNumberOption(index, 'shorten_numbers')"
										@update:modelValue="
											setNumberOption(index, 'shorten_numbers', $event)
										"
									/>
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
											:window="config.window"
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

			<DimensionPicker
				label="Date"
				:options="date_dimensions"
				:model-value="config.date_column as Dimension"
				@update:model-value="config.date_column = $event || {}"
			/>

			<NumberWindowPicker
				v-model="config.window"
				:has-date-column="Boolean(config.date_column?.column_name)"
			/>

			<Toggle
				v-if="config.date_column?.column_name"
				label="Show sparkline"
				v-model="config.sparkline"
			/>

			<InlineFormControlLabel
				v-if="config.date_column?.column_name && config.sparkline"
				label="Color"
			>
				<ColorInput
					:model-value="config.sparkline_color"
					@update:model-value="updateColor($event)"
					placement="left-start"
				/>
			</InlineFormControlLabel>
		</div>
	</CollapsibleSection>
</template>
