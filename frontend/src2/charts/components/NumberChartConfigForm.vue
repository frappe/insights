<script setup lang="ts">
import ColorInput from '@/components/Controls/ColorInput.vue'
import { debounce } from 'frappe-ui'
import { computed, watchEffect } from 'vue'
import DraggableList from '../../components/DraggableList.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { copy } from '../../helpers'
import { FIELDTYPES } from '../../helpers/constants'
import { NumberChartConfig } from '../../types/chart.types'
import { Dimension } from '../../types/query.types'
import { DimensionOption, MeasureOption } from './ChartConfigForm.vue'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	measures: MeasureOption[]
}>()

const config = defineModel<NumberChartConfig>({
	required: true,
	default: () => ({
		number_columns: [],
		comparison: false,
		sparkline: false,
	}),
})

const date_dimensions = computed(() =>
	props.dimensions.filter((d) => FIELDTYPES.DATE.includes(d.data_type))
)

watchEffect(() => {
	if (!config.value.number_columns) {
		config.value.number_columns = props.measures.length ? [copy(props.measures[0])] : []
	}
	if (!config.value.number_columns.length) {
		addNumberColumn()
	}
	if (!config.value.date_column) {
		config.value.date_column = {} as DimensionOption
	}
})

function addNumberColumn() {
	config.value.number_columns.push({} as MeasureOption)
}

const updateColor = debounce((color: string) => {
	config.value.sparkline_color = color
}, 500)
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
								:options="props.measures"
								:model-value="item"
								@update:model-value="Object.assign(item, $event || {})"
								@remove="config.number_columns.splice(index, 1)"
							/>
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
				<FormControl v-model="config.prefix" />
			</InlineFormControlLabel>
			<InlineFormControlLabel label="Suffix">
				<FormControl v-model="config.suffix" />
			</InlineFormControlLabel>
			<InlineFormControlLabel label="Decimal">
				<FormControl v-model="config.decimal" type="number" />
			</InlineFormControlLabel>

			<Checkbox label="Show short numbers" v-model="config.shorten_numbers" />
			<Checkbox label="Show comparison" v-model="config.comparison" />
			<Checkbox
				v-if="config.comparison"
				label="Negative is better"
				v-model="config.negative_is_better"
			/>
			<Checkbox v-if="config.date_column" label="Show sparkline" v-model="config.sparkline" />

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
