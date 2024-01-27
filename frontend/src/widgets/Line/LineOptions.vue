<script setup>
import AxisChartOptions from '@/widgets/AxisChart/AxisChartOptions.vue'

const options = defineModel()
const props = defineProps({
	columns: { type: Array, required: true },
})
</script>

<template>
	<div class="space-y-4">
		<AxisChartOptions seriesType="line" v-model:options="options" :columns="props.columns" />

		<div class="space-y-2 text-gray-600">
			<Checkbox v-model="options.smoothLines" label="Enable Curved Lines" />
		</div>

		<div class="space-y-2 text-gray-600">
			<Checkbox v-model="options.showPoints" label="Show Data Points" />
		</div>

		<div class="space-y-2 text-gray-600">
			<Checkbox v-model="options.showArea" label="Show Area" />
		</div>
	</div>
</template>
