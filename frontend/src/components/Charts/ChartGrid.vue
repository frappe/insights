<template>
	<slot v-bind="$attrs"></slot>
</template>

<script setup>
import { inject } from 'vue'
const props = defineProps({ options: Object, default: () => ({}) })

const chartOptions = inject('options')
const defaults = {
	top: 25,
	bottom: 35,
	left: 20,
	right: 30,
	containLabel: true,
}
chartOptions.grid = { ...defaults, ...props.options }
</script>
