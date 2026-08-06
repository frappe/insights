<script setup lang="ts">
import { WorkbookChart } from '../types/workbook.types'
import { useDashboardAuthoring } from './authoring'
import DashboardView from './DashboardView.vue'

// A dashboard inside the workbook that owns it. It shows what every other
// surface shows — the builder is a viewer that can also write — so all it adds
// is the one thing only the workbook knows: which charts this dashboard may draw
// from.
const props = defineProps<{
	dashboard_name: string
	charts: WorkbookChart[]
}>()

const source = useDashboardAuthoring(props.dashboard_name, props.charts)
</script>

<template>
	<DashboardView :source="source" />
</template>
