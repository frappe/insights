import { createRouter, createWebHistory } from 'vue-router'
import { getOnboardingStatus } from '@/utils/onboarding'

const routes = [
	{
		path: '/setup',
		name: 'Setup',
		component: () => import('@/pages/Onboarding.vue'),
	},
	{
		path: '/',
		redirect: '/dashboard',
	},
	{
		path: '/dashboard',
		name: 'DashboardList',
		component: () => import('@/pages/DashboardList.vue'),
	},
	{
		props: true,
		name: 'Dashboard',
		path: '/dashboard/:name',
		component: () => import('@/pages/Dashboard.vue'),
	},
	{
		path: '/data-source',
		name: 'DataSourceList',
		component: () => import('@/pages/DataSourceList.vue'),
	},
	{
		path: '/query',
		name: 'QueryList',
		component: () => import('@/pages/QueryList.vue'),
	},
	{
		props: true,
		name: 'Query',
		path: '/query/:name',
		component: () => import('@/pages/Query.vue'),
	},
	{
		path: '/settings',
		name: 'Settings',
		component: () => import('@/pages/Settings.vue'),
	},
	{
		path: '/settings/running-queries',
		name: 'Running Queries',
		component: () => import('@/pages/RunningQueries.vue'),
	},
]

let router = createRouter({
	history: createWebHistory('/insights'),
	routes,
})

router.beforeEach(async (to, from, next) => {
	const isLoggedIn = !document.cookie.includes('user_id=Guest')

	if (isLoggedIn) {
		const isOnboarded = await getOnboardingStatus()

		if (!isOnboarded && to.name !== 'Setup') {
			return next('/setup')
		}

		if (isOnboarded && to.name === 'Setup') {
			return next('/')
		}

		if (to.path === '/login') {
			next('/')
		} else {
			next()
		}
	} else if (to.path === '/login') {
		next()
	} else {
		// redirect to frappe login page
		window.location.href = '/login'
	}
})

export default router
