<script setup lang="ts">
import { call } from 'frappe-ui'
import ViewerChart from './ViewerChart.vue'

// A chart on its own page, for whoever the link reaches. It is a read surface
// like any other, so it carries nothing but the reference the URL names.
const props = defineProps<{ chart_name: string }>()

const chart_name = await call('insights.api.shared.get_chart_name', {
	chart_name: props.chart_name,
})
</script>

<template>
	<div class="h-full w-full">
		<ViewerChart :chart="chart_name" />
	</div>
</template>
