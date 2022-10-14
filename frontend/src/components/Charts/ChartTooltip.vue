<template></template>

<script setup>
import { inject, useAttrs } from 'vue'

const options = inject('options')

const { trigger = 'axis', appendToBody = 'true', ...attributes } = useAttrs()

options.tooltip = {
	trigger: trigger,
	appendToBody: appendToBody,
	...attributes,
}
</script>
