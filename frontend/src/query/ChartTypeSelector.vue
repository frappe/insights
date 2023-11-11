<script setup>
import widgets from '@/widgets/widgets'
import { CheckIcon, ChevronDownIcon, Sparkles } from 'lucide-vue-next'
import { computed, inject } from 'vue'

const query = inject('query')

const currentChartType = computed(() => {
	return query.chart.doc?.chart_type
})
const getChartIcon = (chartType) => {
	if (chartType == 'Auto') return Sparkles
	const widget = widgets.get(chartType)
	return widget.icon
}
const AutoChartType = { label: 'Auto', value: 'Auto' }
const chartOptions = computed(() => {
	return [AutoChartType, ...widgets.getChartOptions()]
})
</script>

<template>
	<Autocomplete :return-value="true" :options="chartOptions" v-model="query.chart.doc.chart_type">
		<template #target="{ togglePopover }">
			<Button variant="outline" @click="togglePopover">
				<div class="flex items-center gap-2">
					<component :is="getChartIcon(currentChartType)" class="h-4 w-4 text-gray-600" />
					<span class="truncate">{{ currentChartType }}</span>
					<ChevronDownIcon class="h-4 w-4 text-gray-600" />
				</div>
			</Button>
		</template>

		<template #item-prefix="{ option }">
			<component :is="getChartIcon(option.value)" class="h-4 w-4 text-gray-600" />
		</template>
		<template #item-suffix="{ selected }">
			<CheckIcon v-if="selected" class="h-4 w-4 text-gray-600" />
		</template>
	</Autocomplete>
</template>
