<script setup lang="ts">
import { computed, watchEffect } from 'vue'
import { SplitBy } from '../../types/chart.types'
import { DimensionOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
}>()

const split_by = defineModel<SplitBy>({
	required: true,
	default: () => ({}),
})

watchEffect(() => {
	if (!split_by.value) {
		split_by.value = {
			dimension: {} as DimensionOption,
			max_split_values: 10,
		}
	}
	if (!split_by.value.dimension) {
		split_by.value.dimension = {} as DimensionOption
	}
	if (!split_by.value.max_split_values) {
		split_by.value.max_split_values = 10
	}
})

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
	<CollapsibleSection title="Split Series">
		<div class="flex flex-col gap-3 pt-1">
			<DimensionPicker
				label="Split By"
				:options="props.dimensions"
				:modelValue="dimension"
				@update:modelValue="dimension = $event || {}"
				@remove="dimension = {}"
			/>

			<FormControl
				v-if="dimension?.column_name"
				type="number"
				label="Max Split Values"
				placeholder="10"
				autocomplete="off"
				:modelValue="split_by.max_split_values || 10"
				@update:modelValue="split_by.max_split_values = $event || 10"
			/>
		</div>
	</CollapsibleSection>
</template>
