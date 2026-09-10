<script setup lang="ts">
import { __ } from '../translation'
import DashboardPage from './DashboardPage.vue'
import { useDashboardView } from './view'

// The dashboard page inside Insights. It shows what every other surface shows,
// so all it adds is where this page sits in the app: the trail above it, and the
// name of the tab it is open in.
const props = defineProps<{ name: string }>()

const dashboard = useDashboardView(() => props.name, 'dashboards')

const crumbs = [{ label: __('Dashboards'), route: '/dashboards' }]

function setTitle(title: string) {
	document.title = `${title} | Insights`
}
</script>

<template>
	<DashboardPage :dashboard="dashboard" :breadcrumbs="crumbs" @title="setTitle" />
</template>
