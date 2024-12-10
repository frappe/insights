<script setup lang="ts">
import { computed } from 'vue'
import { FIELDTYPES } from '../../helpers/constants'
import { FunnelChartConfig } from '../../types/chart.types'
import { ColumnOption, DimensionOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import MeasurePicker from './MeasurePicker.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
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
		</div>
	</CollapsibleSection>
</template>
