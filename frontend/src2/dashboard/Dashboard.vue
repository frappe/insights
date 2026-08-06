<script setup lang="ts">
import { call } from 'frappe-ui'
import DashboardView from './DashboardView.vue'
import { __ } from '../translation'

// The dashboard page inside Insights. It shows what every other surface shows,
// so all it adds is where this page sits in the app: the trail above it, and the
// name of the tab it is open in.
const props = defineProps<{ name: string }>()

// A v2 name that survived the rename to v3 is the one reference form the viewer
// does not know, so the route's name is resolved before it is handed over.
const dashboard = (await call('insights.api.shared.get_dashboard_name', {
	dashboard_name: props.name,
})) as string

const crumbs = [{ label: __('Dashboards'), route: '/dashboards' }]

function setTitle(title: string) {
	document.title = `${title} | Insights`
}
</script>

<template>
	<DashboardView :dashboard="dashboard" :breadcrumbs="crumbs" @title="setTitle" />
</template>
