<template></template>

<script setup>
import { inject, useAttrs } from 'vue'

const options = inject('options')

const { trigger = 'axis', ...attributes } = useAttrs()

options.tooltip = {
	trigger: trigger,
	...attributes,
}
</script>
