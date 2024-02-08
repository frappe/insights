<script setup>
import ColorInput from '@/components/Controls/ColorInput.vue'
import { computed } from 'vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	modelValue: { required: true },
	seriesType: { type: String },
})
const series = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})
if (props.seriesType) series.value.type = props.seriesType
if (!series.value.type) series.value.type = 'bar'
</script>

<template>
	<div class="flex flex-col gap-3">
		<div v-if="!props.seriesType">
			<FormControl
				label="Axis Type"
				type="select"
				:options="[
					{ label: 'Line', value: 'line' },
					{ label: 'Bar', value: 'bar' },
				]"
				v-model="series.type"
			/>
		</div>

		<ColorInput label="Color" v-model="series.color" placement="right-start" />

		<template v-if="series.type == 'line'">
			<Checkbox v-model="series.smoothLines" label="Enable Curved Lines" />
			<Checkbox v-model="series.showPoints" label="Show Data Points" />
			<Checkbox v-model="series.showArea" label="Show Area" />
		</template>
	</div>
</template>
