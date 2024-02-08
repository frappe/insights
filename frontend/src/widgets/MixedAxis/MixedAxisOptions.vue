<script setup>
import AxisChartOptions from '@/widgets/AxisChart/AxisChartOptions.vue'

const options = defineModel()
const props = defineProps({
	columns: { type: Array, required: true },
})
</script>

<template>
	<div class="space-y-4">
		<AxisChartOptions v-model:options="options" :columns="props.columns" />
	</div>
</template>
