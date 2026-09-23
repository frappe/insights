<script setup lang="ts">
import { watch } from 'vue'
import router from '../router'
import session from '../session'
import DashboardPage from './DashboardPage.vue'
import { useDashboardView } from './view'

// A dashboard reached by its public link. The view endpoints are the same ones
// the app's own page uses, and they decide access from the visibility level — a
// guest reaches the Public level through that one path, so this page adds no
// access rule of its own.
//
// There is no trail: whoever follows a link here has no place in the app to go
// back to.
const props = defineProps<{ dashboard_name: string }>()

// The route's reference goes over as it arrived: the resolver answers every form
// a link can carry — a route, a docname, or the name it had in v2.
const dashboard = useDashboardView(() => props.dashboard_name, 'shared')

// A visitor whose link opens nothing is offered a sign-in: the dashboard may be
// one a signed-in user can read. A missing and a withdrawn dashboard answer the
// same, so sending both there says nothing about which it was.
watch(
	() => dashboard.notFound,
	(notFound) => {
		if (!notFound || session.isLoggedIn) return
		session.resetSession()
		router.push('/login')
	},
)
</script>

<template>
	<DashboardPage :dashboard="dashboard" />
</template>
