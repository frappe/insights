<script setup>
import widgets from '@/widgets/widgets'
import InvalidWidget from '@/widgets/InvalidWidget.vue'
import usePublicChart from './usePublicChart'
const props = defineProps({ public_key: String })
const chart = usePublicChart(props.public_key)
</script>

<template>
	<component
		v-if="chart.doc.chart_type"
		ref="widget"
		:is="widgets.getComponent(chart.doc.chart_type)"
		:data="chart.data"
		:options="chart.doc.options"
		:key="JSON.stringify(chart.doc.options)"
	/>
</template>
