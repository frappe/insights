<script setup lang="ts">
import { watch } from 'vue'
import router from '../router'
import session from '../session'
import DashboardPage from './DashboardPage.vue'
import { useDashboardView } from './view'

// A dashboard opened by its public link. It uses the same view endpoints as the
// app's own page. They check access, and a guest gets in only through the Public
// visibility level. So this page adds no access rule of its own.
//
// There are no breadcrumbs, because a visitor from a link has no page in the app
// to go back to.
const props = defineProps<{ dashboard_name: string }>()

// The reference is sent unchanged. The resolver accepts every form a link can
// carry: a route, a docname, or the v2 name.
const dashboard = useDashboardView(() => props.dashboard_name, 'shared')

// On Not Found, a guest is sent to sign in, because a signed-in user may be
// able to read the dashboard. A missing dashboard and one that is no longer
// public both answer Not Found, so the redirect does not say which it was.
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
