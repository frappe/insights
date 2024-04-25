<script setup lang="ts">
import widgets, { ChartType } from '@/widgets/widgets'
const chartType = defineModel<ChartType>()
</script>

<template>
	<div class="flex flex-col gap-2 p-3">
		<div class="text-[11px] uppercase text-gray-600">Chart Type</div>
		<div class="grid grid-cols-2 gap-2">
			<Button
				v-for="item in widgets.getChartOptions()"
				:key="item.value"
				variant="outline"
				class="!justify-start"
				:class="
					chartType === item.value
						? 'border-gray-700 hover:border-gray-700'
						: 'border-gray-200'
				"
				@click="chartType = item.value"
			>
				<div class="flex items-center gap-2">
					<component
						:is="widgets.getIcon(item.value)"
						class="h-4 w-4 text-gray-600"
						stroke-width="1.5"
					/>
					<div class="text-xs">{{ item.label }}</div>
				</div>
			</Button>
		</div>
	</div>
</template>
