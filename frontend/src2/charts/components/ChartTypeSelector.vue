<script setup lang="ts">
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { CHARTS, ChartType } from '../../types/chart.types'
import ChartIcon from './ChartIcon.vue'

const chartType = defineModel<ChartType>()
</script>

<template>
	<InlineFormControlLabel label="Chart Type">
		<div class="grid grid-cols-2 gap-2">
			<Button
				v-for="item in CHARTS"
				:key="item"
				variant="subtle"
				class="!justify-start"
				:class="chartType === item ? 'bg-white shadow hover:bg-white' : ''"
				@click="chartType = item"
			>
				<div class="flex items-center gap-1.5">
					<ChartIcon :chartType="item" class="!h-3.5 !w-3.5" />
					<div class="text-sm">{{ item == 'Number' ? 'KPI' : item }}</div>
				</div>
			</Button>
		</div>
	</InlineFormControlLabel>
</template>
