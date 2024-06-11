<script setup lang="ts">
import { computed, inject } from 'vue'
import DashboardBuilder from '../dashboard/DashboardBuilder.vue'
import { Workbook, workbookKey } from './workbook'

const props = defineProps<{ name?: string; index: number | string }>()
const workbook = inject(workbookKey) as Workbook
workbook.setActiveTab('dashboard', Number(props.index))
</script>

<template>
	<DashboardBuilder
		v-if="workbook.activeDashboard"
		:key="workbook.activeDashboard.name"
		:dashboard="workbook.activeDashboard"
		:charts="workbook.doc.charts"
		:queries="workbook.doc.queries"
	/>
</template>
