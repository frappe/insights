<template>
	<slot v-bind="$attrs"></slot>
</template>

<script setup>
import { inject, useAttrs } from 'vue'
const options = inject('options')
const defaults = {
	top: 25,
	bottom: 55,
	left: 45,
	right: 30,
}
options.grid = { ...defaults, ...useAttrs() }
</script>
