<script setup lang="ts">
import ColorInput from '@/components/Controls/ColorInput.vue'
import { debounce } from 'frappe-ui'
import { computed, watchEffect } from 'vue'
import DraggableList from '../../components/DraggableList.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { FIELDTYPES } from '../../helpers/constants'
import { NumberChartConfig, NumberColumnOptions } from '../../types/chart.types'
import { ColumnOption, Dimension, DimensionOption, MeasureOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
}>()

const config = defineModel<NumberChartConfig>({
	required: true,
	default: () => ({
		number_columns: [],
		number_column_options: [],
		comparison: false,
		sparkline: false,
	}),
})

const date_dimensions = computed(() =>
	props.dimensions.filter((d) => FIELDTYPES.DATE.includes(d.data_type))
)

watchEffect(() => {
	if (!config.value.number_columns?.length) {
		addNumberColumn()
	}
	if (!config.value.date_column) {
		config.value.date_column = {} as DimensionOption
	}
	if (!config.value.number_column_options) {
		config.value.number_column_options = []
	}
})

function addNumberColumn() {
	if (!config.value.number_columns) {
		config.value.number_columns = []
	}
	config.value.number_columns.push({} as MeasureOption)
}

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
</script>

<template>
	<CollapsibleSection title="Options">
		<div class="flex flex-col gap-3 pt-1">
			<div>
				<p class="mb-1.5 text-xs text-gray-600">Columns</p>
				<div>
					<DraggableList v-model:items="config.number_columns" group="numbers">
						<template #item="{ item, index }">
							<MeasurePicker
								:model-value="item"
								:column-options="props.columnOptions"
								@update:model-value="Object.assign(item, $event || {})"
								@remove="config.number_columns.splice(index, 1)"
							>
								<template #config-fields>
									<InlineFormControlLabel label="Prefix">
										<FormControl
											autocomplete="off"
											:modelValue="getNumberOption(index, 'prefix')"
											@update:modelValue="
												setNumberOption(index, 'prefix', $event)
											"
										/>
									</InlineFormControlLabel>
									<InlineFormControlLabel label="Suffix">
										<FormControl
											autocomplete="off"
											:modelValue="getNumberOption(index, 'suffix')"
											@update:modelValue="
												setNumberOption(index, 'suffix', $event)
											"
										/>
									</InlineFormControlLabel>
									<InlineFormControlLabel label="Decimal">
										<FormControl
											autocomplete="off"
											:modelValue="getNumberOption(index, 'decimal')"
											@update:modelValue="
												setNumberOption(index, 'decimal', $event)
											"
											type="number"
										/>
									</InlineFormControlLabel>

									<Toggle
										label="Show short numbers"
										:modelValue="getNumberOption(index, 'shorten_numbers')"
										@update:modelValue="
											setNumberOption(index, 'shorten_numbers', $event)
										"
									/>
								</template>
							</MeasurePicker>
						</template>
					</DraggableList>
					<button
						class="mt-1.5 text-left text-xs text-gray-600 hover:underline"
						@click="config.number_columns.push({} as any)"
					>
						+ Add column
					</button>
				</div>
			</div>

			<DimensionPicker
				label="Date"
				:options="date_dimensions"
				:model-value="(config.date_column as Dimension)"
				@update:model-value="config.date_column = $event || {}"
			/>

			<InlineFormControlLabel label="Prefix">
				<FormControl v-model="config.prefix" autocomplete="off" />
			</InlineFormControlLabel>
			<InlineFormControlLabel label="Suffix">
				<FormControl v-model="config.suffix" autocomplete="off" />
			</InlineFormControlLabel>
			<InlineFormControlLabel label="Decimal">
				<FormControl v-model="config.decimal" type="number" autocomplete="off" />
			</InlineFormControlLabel>

			<Toggle label="Show short numbers" v-model="config.shorten_numbers" />

			<Toggle
				v-if="config.date_column?.column_name"
				label="Show comparison"
				v-model="config.comparison"
			/>

			<Toggle
				v-if="config.comparison"
				label="Negative is better"
				v-model="config.negative_is_better"
			/>

			<Toggle v-if="config.comparison" label="Show sparkline" v-model="config.sparkline" />

			<InlineFormControlLabel v-if="config.sparkline" label="Color">
				<ColorInput
					:model-value="config.sparkline_color"
					@update:model-value="updateColor($event)"
					placement="left-start"
				/>
			</InlineFormControlLabel>
		</div>
	</CollapsibleSection>
</template>
