<script setup lang="ts">
import { call } from 'frappe-ui'
import DashboardView from './DashboardView.vue'
import { useSavedDashboard } from './viewer'

// A dashboard reached by its public link. The viewer endpoints are the same ones
// the desk island and the in-app page use, and they decide access through the
// visibility ladder — a guest reaches the Public rung through that one path, so
// this page adds no access rule of its own.
//
// There is no trail: whoever follows a link here has no place in the app to go
// back to.
const props = defineProps<{ dashboard_name: string }>()

// The link may carry a slug, a docname, or a v2 name that survived the rename to
// v3. Only the last is a form the viewer cannot resolve for itself.
const dashboard = (await call('insights.api.shared.get_dashboard_name', {
	dashboard_name: props.dashboard_name,
})) as string

const source = useSavedDashboard(dashboard)

function setTitle(title: string) {
	document.title = `${title} | Insights`
}
</script>

<template>
	<DashboardView :source="source" @title="setTitle" />
</template>
