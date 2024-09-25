<script setup lang="ts">
import { computed } from 'vue'
import { FIELDTYPES } from '../../helpers/constants'
import { FunnelChartConfig } from '../../types/chart.types'
import { DimensionOption, MeasureOption } from './ChartConfigForm.vue'
import CollapsibleSection from './CollapsibleSection.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	measures: MeasureOption[]
}>()

const config = defineModel<FunnelChartConfig>({
	required: true,
	default: () => ({
		label_column: {},
		value_column: {},
	}),
})

const discrete_dimensions = computed(() =>
	props.dimensions.filter((d) => FIELDTYPES.DISCRETE.includes(d.data_type))
)
</script>

<template>
	<CollapsibleSection title="Options">
		<div class="flex flex-col gap-3 pt-1">
			<Autocomplete
				label="Label"
				:showFooter="true"
				:options="discrete_dimensions"
				:modelValue="config.label_column?.column_name"
				@update:modelValue="config.label_column = $event"
			/>
			<Autocomplete
				label="Value"
				:showFooter="true"
				:options="props.measures"
				:modelValue="config.value_column?.measure_name"
				@update:modelValue="config.value_column = $event"
			/>
		</div>
	</CollapsibleSection>
</template>
