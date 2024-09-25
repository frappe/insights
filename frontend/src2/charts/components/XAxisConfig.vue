<script setup lang="ts">
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { FIELDTYPES, granularityOptions } from '../../helpers/constants'
import { AxisChartConfig } from '../../types/chart.types'
import { DimensionOption } from './ChartConfigForm.vue'
import CollapsibleSection from './CollapsibleSection.vue'

const props = defineProps<{ dimensions: DimensionOption[] }>()
const x_axis = defineModel<AxisChartConfig['x_axis']>({
	required: true,
	default: () => ({}),
})
</script>

<template>
	<CollapsibleSection title="X Axis">
		<div class="flex flex-col gap-3 pt-1">
			<InlineFormControlLabel label="Column">
				<Autocomplete
					placeholder="Select a column"
					:showFooter="true"
					:options="props.dimensions"
					:modelValue="x_axis.column_name"
					@update:modelValue="x_axis = $event || {}"
				/>
			</InlineFormControlLabel>
			<InlineFormControlLabel
				v-if="FIELDTYPES.DATE.includes(x_axis.data_type)"
				label="Granularity"
			>
				<Autocomplete
					:hide-search="true"
					:options="granularityOptions"
					:model-value="x_axis.granularity"
					@update:model-value="x_axis.granularity = $event?.value || 'month'"
				/>
			</InlineFormControlLabel>
			<InlineFormControlLabel label="Axis Label">
				<FormControl />
			</InlineFormControlLabel>
		</div>
	</CollapsibleSection>
</template>
