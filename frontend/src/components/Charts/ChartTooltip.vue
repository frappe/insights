<template></template>

<script setup>
import { inject, useAttrs } from 'vue'

const props = defineProps({ options: Object, default: () => ({}) })
const trigger = props.options?.trigger || 'axis'
const confine = props.options?.confine || true
const rest = props.options || {}

const chartOptions = inject('options')
chartOptions.tooltip = {
	trigger: trigger,
	confine: confine,
	...rest,
}
</script>
