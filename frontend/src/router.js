import { createRouter, createWebHistory } from 'vue-router'
import { getOnboardingStatus } from '@/controllers/onboarding'

const routes = [
	{
		path: '/setup',
		name: 'Setup',
		component: () => import('@/pages/Onboarding.vue'),
	},
	{
		path: '/',
		name: 'Home',
		component: () => import('@/pages/Home.vue'),
	},
	{
		path: '/dashboard',
		name: 'Dashboards',
		component: () => import('@/pages/Dashboards.vue'),
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
		name: 'Query',
		props: true,
		path: '/query/:name',
		component: () => import('@/pages/Query.vue'),
	},
	{
		path: '/settings',
		name: 'Settings',
		component: () => import('@/pages/Settings.vue'),
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
