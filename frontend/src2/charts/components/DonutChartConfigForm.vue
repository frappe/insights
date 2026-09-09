<script setup lang="ts">
import { computed } from 'vue'
import { FIELDTYPES } from '../../helpers/constants'
import { DonutChartConfig } from '../../types/chart.types'
import { ColumnOption, DimensionOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'
import NumberFormatSection from './NumberFormatSection.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
}>()

const config = defineModel<DonutChartConfig>({
	required: true,
	default: () => ({
		label_column: {},
		value_column: {},
	}),
})

const discrete_dimensions = computed(() =>
	props.dimensions.filter((d) => FIELDTYPES.DISCRETE.includes(d.data_type)),
)
</script>

<template>
	<CollapsibleSection title="Options">
		<div class="flex flex-col gap-3 pt-1">
			<DimensionPicker
				label="Label"
				v-model="config.label_column"
				:options="discrete_dimensions"
			/>
			<MeasurePicker
				label="Value"
				v-model="config.value_column"
				:column-options="props.columnOptions"
			/>
			<InlineFormControlLabel label="Max slices" control-width="4rem">
				<FormControl v-model="config.max_slices" type="number" min="1" placeholder="10" />
			</InlineFormControlLabel>
			<Toggle v-model="config.show_inline_labels" label="Inline labels" />
		</div>
	</CollapsibleSection>

	<NumberFormatSection :config="config" :sole-measure-name="config.value_column?.measure_name" />
</template>
