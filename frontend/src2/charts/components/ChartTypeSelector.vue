<script setup lang="ts">
import { ChartType, CHARTS } from '../helpers'
import ChartIcon from './ChartIcon.vue'

const chartType = defineModel<ChartType>()
</script>

<template>
	<div class="flex flex-col gap-2 p-3">
		<div class="text-[11px] uppercase">Chart Type</div>
		<div class="grid grid-cols-2 gap-2">
			<Button
				v-for="item in CHARTS"
				:key="item"
				variant="outline"
				class="!justify-start"
				:class="
					chartType === item ? 'border-gray-700 hover:border-gray-700' : 'border-gray-200'
				"
				@click="chartType = item"
			>
				<div class="flex items-center gap-2">
					<ChartIcon :chartType="item" />
					<div class="text-xs">{{ item }}</div>
				</div>
			</Button>
		</div>
	</div>
</template>
