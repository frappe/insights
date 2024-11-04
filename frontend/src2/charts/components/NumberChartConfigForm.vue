<script setup lang="ts">
import { FIELDTYPES } from '../../helpers/constants'
import { computed, watchEffect } from 'vue'
import { debounce } from 'frappe-ui'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { NumberChartConfig } from '../../types/chart.types'
import { DimensionOption, MeasureOption } from './ChartConfigForm.vue'
import CollapsibleSection from './CollapsibleSection.vue'
import { Settings, XIcon } from 'lucide-vue-next'
import { copy } from '../../helpers'
import ColorInput from '@/components/Controls/ColorInput.vue'

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
			<template v-for="(c, idx) in config.number_columns" :key="idx">
				<div class="flex items-end gap-1">
					<div class="flex-1">
						<Autocomplete
							placeholder="Select a column"
							:label="
								config.number_columns.length > 1 ? `Column ${idx + 1}` : 'Column'
							"
							:showFooter="true"
							:options="props.measures"
							:modelValue="c.measure_name"
							@update:modelValue="Object.assign(c, $event || {})"
						/>
					</div>
					<Popover v-if="c.measure_name" placement="bottom-end">
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
										v-model="c.measure_name"
										autocomplete="off"
										:debounce="500"
									/>
								</InlineFormControlLabel>
								<div class="flex gap-1">
									<Button
										class="w-full"
										@click="config.number_columns.splice(idx, 1)"
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
					<Button
						v-else
						class="flex-shrink-0"
						@click="config.number_columns.splice(idx, 1)"
					>
						<template #icon>
							<XIcon class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
				</div>
			</template>
			<button
				class="-mt-1 text-left text-xs text-gray-600 hover:underline"
				@click="addNumberColumn"
			>
				+ Add column
			</button>

			<InlineFormControlLabel label="Date">
				<Autocomplete
					:showFooter="true"
					:options="date_dimensions"
					:modelValue="config.date_column?.column_name"
					@update:modelValue="config.date_column = $event"
				/>
			</InlineFormControlLabel>

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
