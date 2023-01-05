import { createRouter, createWebHistory } from 'vue-router'
import { getSetupStatus } from '@/utils/setupWizard'
import { getOnboardingStatus } from '@/utils/onboarding'
import auth from '@/utils/auth'

const routes = [
	{
		path: '/setup',
		name: 'Setup',
		component: () => import('@/pages/SetupWizard.vue'),
		meta: {
			hideSidebar: true,
		},
	},
	{
		path: '/login',
		name: 'Login',
		component: () => import('@/pages/Login.vue'),
		meta: {
			isLoginPage: true,
			hideSidebar: true,
		},
	},
	{
		path: '/',
		redirect: '/get-started',
	},
	{
		path: '/get-started',
		name: 'Get Started',
		component: () => import('@/pages/GetStarted.vue'),
	},
	{
		path: '/dashboard',
		name: 'Dashboards',
		component: () => import('@/dashboard/Dashboards.vue'),
	},
	{
		props: true,
		name: 'Dashboard',
		path: '/dashboard/:name',
		component: () => import('@/dashboard/Dashboard.vue'),
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
		props: true,
		name: 'DataSourceTable',
		path: '/data-source/:name/:table',
		component: () => import('@/pages/DataSourceTable.vue'),
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
		path: '/teams',
		name: 'Teams',
		component: () => import('@/pages/Teams.vue'),
		meta: {
			isAllowed: () => auth.user.is_admin,
		},
	},
	{
		path: '/settings',
		name: 'Settings',
		component: () => import('@/pages/Settings.vue'),
	},
	{
		path: '/no-permission',
		name: 'No Permission',
		component: () => import('@/pages/NoPermission.vue'),
		meta: {
			hideSidebar: true,
		},
	},
	{
		path: '/not-found',
		name: 'Not Found',
		component: () => import('@/pages/NotFound.vue'),
		meta: {
			hideSidebar: true,
		},
	},
]

let router = createRouter({
	history: createWebHistory('/insights'),
	routes,
})

router.beforeEach(async (to, from, next) => {
	if (!auth.isLoggedIn) {
		// if in dev mode, open login page
		if (import.meta.env.DEV) {
			return to.fullPath === '/login' ? next() : next('/login')
		}
		// redirect to frappe login page, for oauth and signup
		window.location.href = '/login'
		return next(false)
	}

	const isAuthorized = await auth.isAuthorized()
	if (!isAuthorized && to.name !== 'No Permission') {
		return next('/no-permission')
	}
	if (isAuthorized && to.name === 'No Permission') {
		return next()
	}
	if (to.meta.isAllowed && !to.meta.isAllowed()) {
		return next('/no-permission')
	}

	// force redirect to Setup page if database not set up yet
	const setupComplete = await getSetupStatus()
	if (!setupComplete && to.name !== 'Setup') {
		return next('/setup')
	}
	if (setupComplete && to.name === 'Setup') {
		return next('/')
	}

	// redirect to /dashboard if onboarding is complete
	const onboardingComplete = await getOnboardingStatus()
	if (onboardingComplete && to.name == 'Get Started') {
		return next('/dashboard')
	}

	if (to.path === '/login') {
		next('/')
	} else {
		next()
	}
})

const _fetch = window.fetch
window.fetch = async function () {
	const res = await _fetch(...arguments)
	if (res.status === 403 && (!document.cookie || document.cookie.includes('user_id=Guest'))) {
		auth.reset()
		router.push('/login')
	}
	return res
}

export default router
