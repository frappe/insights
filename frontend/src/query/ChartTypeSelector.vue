<script setup>
import widgets from '@/widgets/widgets'
import { CheckIcon, ChevronDownIcon } from 'lucide-vue-next'
import { computed, inject } from 'vue'

const query = inject('query')
if (!query.chart.doc.chart_type) {
	query.chart.doc.chart_type = 'Auto'
}
const currentChartType = computed(() => {
	return query.chart.doc?.chart_type
})
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
					<component
						:is="widgets.getIcon(currentChartType)"
						class="h-4 w-4 text-gray-600"
					/>
					<span class="truncate">{{ currentChartType }}</span>
					<ChevronDownIcon class="h-4 w-4 text-gray-600" />
				</div>
			</Button>
		</template>

		<template #item-prefix="{ option }">
			<component :is="widgets.getIcon(option.value)" class="h-4 w-4 text-gray-600" />
		</template>
		<template #item-suffix="{ selected }">
			<CheckIcon v-if="selected" class="h-4 w-4 text-gray-600" />
		</template>
	</Autocomplete>
</template>
