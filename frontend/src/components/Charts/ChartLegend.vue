<template></template>

<script setup>
import { inject, useAttrs } from 'vue'

const props = defineProps({ options: Object, default: () => ({}) })

const chartOptions = inject('options')
const type = props.options?.type || 'plain'
const rest = props.options || {}
chartOptions.legend = {
	type: type,
	icon: 'circle',
	pageIconSize: 12,
	pageIconColor: '#64748B',
	pageIconInactiveColor: '#C0CCDA',
	pageFormatter: '{current}',
	pageButtonItemGap: 2,
	...rest,
}
</script>
