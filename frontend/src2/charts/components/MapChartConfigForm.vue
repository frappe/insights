<script setup lang="ts">
import { computed, onMounted, watch, watchEffect } from 'vue'
import { MapChartConfig } from '../../types/chart.types'
import { DimensionOption, ColumnOption, Measure, Dimension } from '../../types/query.types'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'
import CollapsibleSection from './CollapsibleSection.vue'
import { FormControl } from 'frappe-ui'
import { FIELDTYPES } from '../../helpers/constants'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
}>()

const config = defineModel<MapChartConfig>({
	required: true,
	default: () => ({
		location_column: {},
		value_column: {},
		map_type: 'world',
	}),
})

watchEffect(() => {
	if (!config.value.location_column) {
		config.value.location_column = {} as Dimension
	}
	if (!config.value.value_column) {
		config.value.value_column = {} as Measure
	}
})

const discrete_dimensions = computed(() =>
	props.dimensions.filter((d) => FIELDTYPES.DISCRETE.includes(d.data_type)),
)

const map_options = [
	{ label: 'World Map', value: 'world' },
	{ label: 'India', value: 'india' },
]
</script>

<template>
	<CollapsibleSection title="Options">
		<div class="flex flex-col gap-3 pt-1">
			<FormControl
				v-model="config.map_type"
				label="Map Type"
				type="select"
				:options="map_options"
			/>

			<DimensionPicker
				v-model="config.location_column"
				:options="discrete_dimensions"
				label="Region Column"
			/>

			<MeasurePicker
				v-model="config.value_column"
				:column-options="props.columnOptions"
				label="Value"
			/>
		</div>
	</CollapsibleSection>
</template>
