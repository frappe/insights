<script setup>
import { computed } from 'vue'

const props = defineProps({
	progress: {
		type: Number,
		default: 0,
	},
	progressLabel: {
		type: String,
		default: '',
	},
	radius: {
		type: Number,
		default: 26,
	},
	stroke: {
		type: Number,
		default: 4,
	},
})

const normalizedRadius = computed(() => props.radius - props.stroke * 2)
const circumference = computed(() => normalizedRadius.value * 2 * Math.PI)
const strokeDashoffset = computed(
	() => circumference.value - (props.progress / 100) * circumference.value
)
</script>

<template>
	<div class="relative flex items-center justify-center rounded-full">
		<svg :height="radius * 2" :width="radius * 2">
			<circle
				class="text-gray-300"
				stroke="currentColor"
				fill="transparent"
				:stroke-width="stroke"
				:r="normalizedRadius"
				:cx="radius"
				:cy="radius"
			/>
			<circle
				class="text-gray-900"
				stroke-linecap="round"
				stroke="currentColor"
				fill="transparent"
				:stroke-width="stroke"
				:stroke-dasharray="circumference"
				:stroke-dashoffset="strokeDashoffset"
				:r="normalizedRadius"
				:cx="radius"
				:cy="radius"
			/>
		</svg>
		<span class="absolute font-bold">
			{{ progressLabel }}
		</span>
	</div>
</template>

<style scoped>
circle {
	transition: stroke-dashoffset 0.35s;
	transform: rotate(-90deg);
	transform-origin: 50% 50%;
}
</style>
