<template></template>

<script setup>
import { inject, useAttrs } from 'vue'

const { title, subtitle } = useAttrs()
const options = inject('options')
options.title = {
	text: title,
	subtext: subtitle,
	textStyle: {
		fontSize: 15,
		fontWeight: 500,
	},
	subtextStyle: {
		fontSize: 12,
		fontWeight: 400,
	},
}
</script>
