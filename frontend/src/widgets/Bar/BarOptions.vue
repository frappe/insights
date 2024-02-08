<script setup>
import Autocomplete from '@/components/Controls/Autocomplete.vue'

import ColorPalette from '@/components/Controls/ColorPalette.vue'
import DraggableList from '@/components/DraggableList.vue'
import DraggableListItemMenu from '@/components/DraggableListItemMenu.vue'
import { FIELDTYPES } from '@/utils'
import { computed } from 'vue'
import SeriesOption from '../SeriesOption.vue'
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
	</div>
</template>
