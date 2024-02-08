<script setup>
import AxisChartOptions from '@/widgets/AxisChart/AxisChartOptions.vue'

const options = defineModel()
const props = defineProps({
	columns: { type: Array, required: true },
})
</script>

<template>
	<div class="space-y-4">
		<AxisChartOptions seriesType="bar" v-model:options="options" :columns="props.columns" />
		<Checkbox v-model="options.stack" label="Stack Values" />
		<Checkbox v-model="options.roundedBars" label="Rounded Bars" />
	</div>
</template>
