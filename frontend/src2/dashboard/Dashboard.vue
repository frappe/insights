<script setup lang="ts">
import DashboardView from './DashboardView.vue'
import { useSavedDashboard } from './viewer'
import { __ } from '../translation'

// The dashboard page inside Insights. It shows what every other surface shows,
// so all it adds is where this page sits in the app: the trail above it, and the
// name of the tab it is open in.
const props = defineProps<{ name: string }>()

const source = useSavedDashboard(props.name)

const crumbs = [{ label: __('Dashboards'), route: '/dashboards' }]

function setTitle(title: string) {
	document.title = `${title} | Insights`
}
</script>

<template>
	<DashboardView :source="source" :breadcrumbs="crumbs" @title="setTitle" />
</template>
