<script setup lang="ts">
import { inject, ref } from 'vue'
import DashboardBuilder from '../dashboard/DashboardBuilder.vue'
import useDashboard from '../dashboard/dashboard'
import { workbookKey } from './workbook_key'
import { mirrorTitleToWorkbook } from './workbook_items'
import { useRouter } from 'vue-router'

const props = defineProps<{ workbook_name?: string; dashboard_name: string }>()

const router = useRouter()
const workbook = inject(workbookKey)!

let dashboard_name = ref(props.dashboard_name)
const index = Number(props.dashboard_name)
if (
	index >= 0 &&
	workbook.doc.dashboards[index] &&
	!workbook.doc.dashboards.find((q) => q.name === props.dashboard_name)
) {
	dashboard_name.value = workbook.doc.dashboards[index].name
	router.replace(`/workbook/${workbook.doc.name}/dashboard/${dashboard_name.value}`)
}

mirrorTitleToWorkbook(useDashboard(dashboard_name.value), 'dashboard')
</script>

<template>
	<DashboardBuilder :dashboard_name="dashboard_name" :charts="workbook.doc.charts" />
</template>
