<template></template>

<script setup>
import { inject, useAttrs } from 'vue'

const options = inject('options')

const { trigger = 'axis', confine = true, ...attributes } = useAttrs()

options.tooltip = {
	trigger: trigger,
	...attributes,
}
</script>
