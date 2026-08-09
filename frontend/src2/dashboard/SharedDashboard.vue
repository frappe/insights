<script setup lang="ts">
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

// The route's reference goes over as it arrived: the viewer resolves every form
// a link can carry.
const source = useSavedDashboard(props.dashboard_name)

function setTitle(title: string) {
	document.title = `${title} | Insights`
}
</script>

<template>
	<DashboardView :source="source" @title="setTitle" />
</template>
