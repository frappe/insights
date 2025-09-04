<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { MapChartConfig } from '../../types/chart.types'
import { DimensionOption, ColumnOption } from '../../types/query.types'
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
		location_column: {
			column_name: '',
			data_type: 'String',
			dimension_name: '',
		},
		value_column: {
			column_name: '',
			data_type: 'Integer',
			measure_name: '',
			aggregation: 'sum',
		},
		city_column: {
			column_name: '',
			data_type: 'String',
			dimension_name: '',
		},
		map_type: 'world',
	}),
})

const initializeConfig = () => {
	if (!config.value) {
		config.value = {
			location_column: {
				column_name: '',
				data_type: 'String',
				dimension_name: '',
			},
			value_column: {
				column_name: '',
				data_type: 'Integer',
				measure_name: '',
				aggregation: 'sum',
			},
			city_column: {
				column_name: '',
				data_type: 'String',
				dimension_name: '',
			},
			map_type: 'world',
			india_region: 'states',
		}
	} else {
		if (!config.value.location_column) {
			config.value.location_column = {
				column_name: '',
				data_type: 'String',
				dimension_name: '',
			}
		}
		if (!config.value.value_column) {
			config.value.value_column = {
				column_name: '',
				data_type: 'Integer',
				measure_name: '',
				aggregation: 'sum',
			}
		}
		if (!config.value.city_column) {
			config.value.city_column = {
				column_name: '',
				data_type: 'String',
				dimension_name: '',
			}
		}
		if (!config.value.map_type) {
			config.value.map_type = 'world'
		}
		if (config.value.map_type === 'india' && !config.value.india_region) {
			config.value.india_region = 'states'
		}
	}
}

onMounted(() => {
	initializeConfig()
})

watch(
	() => config.value?.map_type,
	(newMapType) => {
		if (newMapType === 'india' && !config.value.india_region) {
			config.value.india_region = 'states'
		}
	},
)

const discrete_dimensions = computed(() =>
	props.dimensions.filter((d) => FIELDTYPES.DISCRETE.includes(d.data_type)),
)

const map_options = computed(() => [
	{ label: 'World Map', value: 'world' },
	{ label: 'India', value: 'india' },
])
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

			<template v-if="config.map_type === 'india'">
				<DimensionPicker
					v-model="config.city_column"
					:options="discrete_dimensions"
					label="City Column"
				/>
			</template>
		</div>
	</CollapsibleSection>
</template>
