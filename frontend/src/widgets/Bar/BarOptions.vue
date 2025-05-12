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
		<FormControl
			type="select"
			label="Rotate Labels"
			v-model="options.rotateLabels"
			:options="['0', '45', '90']"
		/>

		<Checkbox v-model="options.stack" label="Stack Values" />
		<Checkbox v-model="options.roundedBars" label="Rounded Bars" />
		<Checkbox v-model="options.show_data_labels" label="Show Data Labels" />
	</div>
</template>
