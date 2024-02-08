<script setup>
import ColorPalette from '@/components/Controls/ColorPalette.vue'
import AxisChartOptions from '@/widgets/AxisChart/AxisChartOptions.vue'

const emit = defineEmits(['update:modelValue'])
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
