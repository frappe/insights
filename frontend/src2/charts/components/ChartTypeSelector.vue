<script setup lang="ts">
import { CHARTS, ChartType } from '../../types/chart.types'
import ChartIcon from './ChartIcon.vue'

const chartType = defineModel<ChartType>()

// A `bg-*` utility beside the variant's own races it on stylesheet order, which
// made the selection read as unselected. Switch the whole variant instead.
function variantFor(item: ChartType) {
	return chartType.value === item ? 'outline' : 'subtle'
}
</script>

<template>
	<div class="grid grid-cols-3 gap-2 pt-0.5">
		<Button
			v-for="item in CHARTS"
			:key="item"
			:variant="variantFor(item)"
			class="!justify-start"
			:class="chartType === item ? '!border-transparent shadow-sm' : ''"
			@click="chartType = item"
		>
			<div class="flex items-center gap-1.5">
				<ChartIcon :chartType="item" class="!h-3.5 !w-3.5" />
				<div class="text-sm">{{ item }}</div>
			</div>
		</Button>
	</div>
</template>
