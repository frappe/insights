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
	>
		<template #placeholder>
			<InvalidWidget
				class="absolute"
				title="Insufficient options"
				message="Please check the options for this chart"
				icon="settings"
				icon-class="text-gray-500"
			/>
		</template>
	</component>
</template>
