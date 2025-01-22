<script setup lang="ts">
import { inject } from 'vue'
import DashboardBuilder from '../dashboard/DashboardBuilder.vue'
import { workbookKey } from './workbook'

const props = defineProps<{ workbook_name?: string; dashboard_name: string }>()

const workbook = inject(workbookKey)!
</script>

<template>
	<DashboardBuilder
		:dashboard_name="props.dashboard_name"
		:charts="workbook.doc.charts"
		:queries="workbook.doc.queries"
	/>
</template>
