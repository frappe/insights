<script setup lang="ts">
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { CHARTS, ChartType } from '../../types/chart.types'
import ChartIcon from './ChartIcon.vue'

const chartType = defineModel<ChartType>()
</script>

<template>
	<InlineFormControlLabel label="Chart Type">
		<Autocomplete
			:options="
				CHARTS.map((item) => {
					return {
						label: item,
						value: item,
					}
				})
			"
			:modelValue="chartType"
			@update:modelValue="chartType = $event?.value"
		>
			<template #prefix>
				<ChartIcon v-if="chartType" :chartType="chartType" />
			</template>
			<template #item-prefix="{ option }">
				<ChartIcon :chartType="option.value" />
			</template>
		</Autocomplete>
	</InlineFormControlLabel>
</template>
