<script setup lang="ts">
import ViewerChart from './ViewerChart.vue'

// A chart on its own page, for whoever the link reaches. It is a read surface
// like any other, so it carries nothing but the reference the URL names.
const props = defineProps<{ chart_name: string }>()
</script>

<template>
	<div class="h-full w-full">
		<ViewerChart :chart="props.chart_name" />
	</div>
</template>
