<script setup lang="ts">
import { computed, watchEffect } from 'vue'
import { __ } from '../../translation'
import { FIELDTYPES } from '../../helpers/constants'
import { DonutChartConfig } from '../../types/chart.types'
import { ColumnOption, Dimension, DimensionOption, Measure } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
}>()

const config = defineModel<DonutChartConfig>({
	required: true,
	default: () => ({
		label_column: {},
		value_column: {},
		label_colors: [],
	}),
})

watchEffect(() => {
	if (!config.value.label_column) {
		config.value.label_column = {} as Dimension
	}
	if (!config.value.value_column) {
		config.value.value_column = {} as Measure
	}
	if (!config.value.label_colors) {
		config.value.label_colors = []
	}
})

const discrete_dimensions = computed(() =>
	props.dimensions.filter((d) => FIELDTYPES.DISCRETE.includes(d.data_type)),
)

const colorPalettes = [
	{ label: 'Default', colors: [] },
	{ label: 'Pastel', colors: ['#FFB3BA', '#FFDFBA', '#FFFFBA', '#BAFFC9', '#BAE1FF'] },
	{ label: 'Bold', colors: ['#E63946', '#F4A261', '#2A9D8F', '#457B9D', '#6A4C93'] },
	{ label: 'Earth', colors: ['#A0522D', '#CD853F', '#DEB887', '#8FBC8F', '#556B2F'] },
	{ label: 'Ocean', colors: ['#03045E', '#0077B6', '#00B4D8', '#90E0EF', '#CAF0F8'] },
]

function applyPalette(colors: string[]) {
	config.value.label_colors = [...colors]
}
</script>

<template>
	<CollapsibleSection title="Options">
		<div class="flex flex-col gap-3 pt-1">
			<DimensionPicker
				label="Label"
				v-model="config.label_column"
				:options="discrete_dimensions"
			/>

			<div class="flex flex-col gap-1.5">
				<span class="text-sm text-gray-600">{{ __('Color Palette') }}</span>
				<div class="flex flex-wrap gap-2">
					<button
						v-for="palette in colorPalettes"
						:key="palette.label"
						class="flex items-center gap-1 rounded border px-2 py-1 text-xs hover:bg-gray-50"
						:class="{
							'border-blue-500 bg-blue-50':
								palette.colors.length === 0
									? !config.label_colors?.length
									: JSON.stringify(config.label_colors) === JSON.stringify(palette.colors),
							'border-gray-200': !(
								palette.colors.length === 0
									? !config.label_colors?.length
									: JSON.stringify(config.label_colors) === JSON.stringify(palette.colors)
							),
						}"
						@click="applyPalette(palette.colors)"
					>
						<span
							v-if="palette.colors.length"
							class="flex gap-0.5"
						>
							<span
								v-for="color in palette.colors.slice(0, 5)"
								:key="color"
								class="inline-block h-3 w-3 rounded-full"
								:style="{ backgroundColor: color }"
							/>
						</span>
						<span v-else class="flex gap-0.5">
							<span
								v-for="c in ['#5470c6','#91cc75','#fac858','#ee6666','#73c0de']"
								:key="c"
								class="inline-block h-3 w-3 rounded-full"
								:style="{ backgroundColor: c }"
							/>
						</span>
						<span class="ml-1 text-gray-600">{{ __(palette.label) }}</span>
					</button>
				</div>

				<div v-if="config.label_colors?.length" class="flex flex-wrap gap-1 pt-1">
					<div
						v-for="(color, idx) in config.label_colors"
						:key="idx"
						class="flex items-center gap-1"
					>
						<input
							type="color"
							:value="color"
							class="h-6 w-6 cursor-pointer rounded border border-gray-200 p-0"
							@input="(e) => {
								const updated = [...(config.label_colors || [])]
								updated[idx] = (e.target as HTMLInputElement).value
								config.label_colors = updated
							}"
						/>
					</div>
				</div>
			</div>

			<MeasurePicker
				label="Value"
				v-model="config.value_column"
				:column-options="props.columnOptions"
			/>
			<FormControl
				v-if="!config.show_inline_labels"
				v-model="config.legend_position"
				label="Legend Position"
				type="select"
				:options="[
					{ label: __('Top'), value: 'top' },
					{ label: __('Bottom'), value: 'bottom' },
					{ label: __('Left'), value: 'left' },
					{ label: __('Right'), value: 'right' },
				]"
			/>
			<FormControl v-model="config.max_slices" label="Max Slices" type="number" min="1" />
			<Toggle v-model="config.show_inline_labels" label="Inline Labels" />
		</div>
	</CollapsibleSection>
</template>
