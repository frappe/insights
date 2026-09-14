<script setup lang="ts">
import { computed } from 'vue'
import { SplitBy } from '../../types/chart.types'
import { DimensionOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import DimensionPicker from './DimensionPicker.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
}>()

const split_by = defineModel<SplitBy>({
	required: true,
	default: () => ({}),
})

// Nothing is seeded here. Writing the config on mount is one autosave and two
// re-runs of the chart data for opening a chart, and the count the server falls
// back to is the count the input shows as its placeholder.

// TODO: debug why v-model="split_by.dimension" doesn't work
const dimension = computed({
	get: () => split_by.value.dimension,
	set: (value) => {
		split_by.value = {
			...split_by.value,
			dimension: value || ({} as DimensionOption),
		}
	},
})
</script>

<template>
	<CollapsibleSection :title="__('Split Series')">
		<div class="flex flex-col gap-3 pt-1">
			<DimensionPicker
				:label="__('Split by')"
				:options="props.dimensions"
				:modelValue="dimension"
				@update:modelValue="dimension = $event || {}"
				@remove="dimension = {}"
			/>

			<InlineFormControlLabel
				v-if="dimension?.column_name"
				:label="__('Max values')"
				control-width="4rem"
			>
				<FormControl
					type="number"
					placeholder="10"
					autocomplete="off"
					:modelValue="split_by.max_split_values"
					@update:modelValue="split_by.max_split_values = $event"
				/>
			</InlineFormControlLabel>
		</div>
	</CollapsibleSection>
</template>
