<script setup lang="ts">
import { __ } from '../translation'
import DashboardPage from './DashboardPage.vue'
import { useDashboardView } from './view'

// The dashboard page in the Insights app. It adds only the breadcrumbs to what
// every other page shows.
const props = defineProps<{ name: string }>()

const dashboard = useDashboardView(() => props.name, 'dashboards')

const crumbs = [{ label: __('Dashboards'), route: '/dashboards' }]
</script>

<template>
	<DashboardPage :dashboard="dashboard" :breadcrumbs="crumbs" />
</template>
