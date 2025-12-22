<script setup lang="ts">
import { computed, ref, watch, watchEffect } from 'vue'
import { MapChartConfig } from '../../types/chart.types'
import {
	DimensionOption,
	ColumnOption,
	Measure,
	Dimension,
	QueryResult,
} from '../../types/query.types'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'
import CollapsibleSection from './CollapsibleSection.vue'
import RegionMappingDialog from './RegionMappingDialog.vue'
import { FormControl, Button, Badge } from 'frappe-ui'
import { FIELDTYPES } from '../../helpers/constants'
import { call } from 'frappe-ui'
import useQuery from '../../query/query'
import { InfoIcon } from 'lucide-vue-next'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
	chartName?: string
	queryResult?: QueryResult
	queryName?: string
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
	props.dimensions.filter((d) => FIELDTYPES.DISCRETE.includes(d.data_type))
)

const map_options = [
	{ label: 'World Map', value: 'world' },
	{ label: 'India', value: 'india' },
]

const showRegionMappingDialog = ref(false)
const unresolvedCount = ref<number | null>(null)
const loadingUnresolved = ref(false)

const userRegions = ref<string[]>([])

watch(
	() => config.value.location_column?.dimension_name,
	async (columnName) => {
		if (!columnName || !props.queryName) {
			userRegions.value = []
			return
		}

		try {
			const chartQuery = useQuery(props.queryName)
			if (!chartQuery) {
				console.warn('No query found')
				return
			}
			const distinctValues = await chartQuery.getDistinctColumnValues(columnName, '', 500)
			userRegions.value = distinctValues.map((val: any) => String(val)).filter(Boolean)
		} catch (error) {
			console.error(error)
			userRegions.value = []
		}
	},
	{ immediate: true }
)

const canCheckRegions = computed(() => {
	const canCheck =
		props.chartName &&
		config.value.map_type &&
		config.value.location_column?.dimension_name &&
		userRegions.value.length > 0

	return canCheck
})

async function checkUnresolvedRegions() {
	if (!canCheckRegions.value) {
		return
	}

	loadingUnresolved.value = true
	try {
		const response = await call('insights.api.maps.find_unresolved_regions', {
			map_type: config.value.map_type,
			user_regions: userRegions.value,
			chart_name: props.chartName,
		})
		unresolvedCount.value = response.unresolved_count
	} catch (error) {
		console.error('Failed to check unresolved regions:', error)
		unresolvedCount.value = null
	} finally {
		loadingUnresolved.value = false
	}
}

function openRegionMappingDialog() {
	showRegionMappingDialog.value = true
}

// Emit event to refresh the chart
async function handleMappingsSaved() {
	await checkUnresolvedRegions()
	emit('mappingsSaved')
}

const emit = defineEmits<{
	mappingsSaved: []
}>()

// Check unresolved regions when data changes
watch(
	[
		() => config.value.map_type,
		() => config.value.location_column?.dimension_name,
		() => userRegions.value.length,
	],
	() => {
		if (canCheckRegions.value) {
			checkUnresolvedRegions()
		}
	}
)
</script>

<template>
	<div class="flex flex-col gap-3">
		<CollapsibleSection title="Options">
			<div class="flex flex-col gap-3 pt-1">
				<FormControl
					v-model="config.map_type"
					label="Map Type"
					type="select"
					:options="map_options"
				/>

				<div class="flex flex-col gap-1">
					<div class="flex items-center gap-1">
						<label class="text-xs text-gray-600">Region Column</label>
						<Button
							v-if="canCheckRegions"
							variant="ghost"
							:icon="InfoIcon"
							@click="openRegionMappingDialog"
							:class="{
								'text-gray-600': unresolvedCount === 0,
								'text-red-600': unresolvedCount !== null && unresolvedCount > 0,
							}"
						/>
					</div>
					<DimensionPicker
						v-model="config.location_column"
						:options="discrete_dimensions"
					/>
				</div>

				<MeasurePicker
					v-model="config.value_column"
					:column-options="props.columnOptions"
					label="Value"
				/>
			</div>
		</CollapsibleSection>

		<RegionMappingDialog
			v-if="chartName"
			v-model="showRegionMappingDialog"
			:chart-name="chartName"
			:map-type="config.map_type"
			:user-regions="userRegions"
			@mappingsSaved="handleMappingsSaved"
		/>
	</div>
</template>
