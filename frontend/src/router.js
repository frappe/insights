import { createRouter, createWebHistory } from 'vue-router'
import { getOnboardingStatus } from '@/utils/onboarding'
import { isLoggedIn, resetAuth } from '@/utils/auth'

const routes = [
	{
		path: '/setup',
		name: 'Setup',
		component: () => import('@/pages/Onboarding.vue'),
	},
	{
		path: '/login',
		name: 'Login',
		component: () => import('@/pages/Login.vue'),
		meta: {
			isLoginPage: true,
		},
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
		props: true,
		name: 'DataSource',
		path: '/data-source/:name',
		component: () => import('@/pages/DataSource.vue'),
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
	if (isLoggedIn.value) {
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
	} else {
		if (!to.meta.isLoginPage) {
			next({ name: 'Login', query: { route: to.path } })
		} else {
			next()
		}
	}
})

const _fetch = window.fetch
window.fetch = async function () {
	const res = await _fetch(...arguments)
	if (res.ok) {
		return res
	}
	if (res.status === 403 && document.cookie.includes('user_id=Guest')) {
		resetAuth()
		router.push('/login')
	}
	return res
}

export default router
