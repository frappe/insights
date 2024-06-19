import sessionStore from '@/stores/sessionStore'
import { createRouter, createWebHistory } from 'vue-router'
import settingsStore from './stores/settingsStore'

const routes = [
	{
		path: '/setup',
		name: 'Setup',
		component: () => import('@/setup/Setup.vue'),
		meta: {
			hideSidebar: true,
		},
	},
	{
		path: '/login',
		name: 'Login',
		component: () => import('@/pages/Login.vue'),
		meta: {
			hideSidebar: true,
			isGuestView: true,
		},
	},
	{
		path: '/',
		name: 'Home',
		component: () => import('@/home/Home.vue'),
	},
	{
		path: '/dashboard',
		name: 'Dashboards',
		component: () => import('@/dashboard/DashboardList.vue'),
	},
	{
		props: true,
		name: 'Dashboard',
		path: '/dashboard/:name',
		component: () => import('@/dashboard/Dashboard.vue'),
	},
	{
		props: true,
		name: 'PublicDashboard',
		path: '/public/dashboard/:public_key',
		component: () => import('@/dashboard/PublicDashboard.vue'),
		meta: {
			hideSidebar: true,
			isGuestView: true,
		},
	},
	{
		props: true,
		name: 'PublicChart',
		path: '/public/chart/:public_key',
		component: () => import('@/query/PublicChart.vue'),
		meta: {
			hideSidebar: true,
			isGuestView: true,
		},
	},
	{
		path: '/data-source',
		name: 'DataSourceList',
		component: () => import('@/datasource/DataSourceList.vue'),
	},
	{
		props: true,
		name: 'DataSource',
		path: '/data-source/:name',
		component: () => import('@/datasource/DataSource.vue'),
	},
	{
		props: true,
		name: 'DataSourceRelationships',
		path: '/data-source/:name/relationships',
		component: () => import('@/datasource/DataSourceRelationships.vue'),
	},
	{
		props: true,
		name: 'DataSourceTable',
		path: '/data-source/:name/:table',
		component: () => import('@/datasource/DataSourceTable.vue'),
	},
	{
		path: '/query',
		name: 'QueryList',
		component: () => import('@/query/QueryList.vue'),
	},
	{
		props: true,
		name: 'Query',
		path: '/query/build/:name',
		component: () => import('@/query/Query.vue'),
	},
	{
		path: '/users',
		name: 'Users',
		component: () => import('@/pages/Users.vue'),
		meta: {
			isAllowed(): boolean {
				return sessionStore().user.is_admin && settingsStore().settings.enable_permissions
			},
		},
	},
	{
		path: '/teams',
		name: 'Teams',
		component: () => import('@/pages/Teams.vue'),
		meta: {
			isAllowed(): boolean {
				return sessionStore().user.is_admin && settingsStore().settings.enable_permissions
			},
		},
	},
	{
		path: '/notebook',
		name: 'NotebookList',
		component: () => import('@/notebook/NotebookList.vue'),
	},
	{
		props: true,
		path: '/notebook/:notebook',
		name: 'Notebook',
		component: () => import('@/notebook/Notebook.vue'),
	},
	{
		props: true,
		path: '/notebook/:notebook/:name',
		name: 'NotebookPage',
		component: () => import('@/notebook/NotebookPage.vue'),
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
		path: '/trial-expired',
		name: 'Trial Expired',
		component: () => import('@/pages/TrialExpired.vue'),
		meta: {
			hideSidebar: true,
		},
	},
	{
		path: '/:pathMatch(.*)*',
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

router.beforeEach(async (to, _, next) => {
	const session = sessionStore()
	!session.initialized && (await session.initialize())

	if (to.meta.isGuestView && !session.isLoggedIn && to.name !== 'Login') {
		// if page is allowed for guest, and is not login page, allow
		return next()
	}

	// route to login page if not logged in
	if (!session.isLoggedIn) {
		// if in dev mode, open login page
		if (import.meta.env.DEV) {
			return to.fullPath === '/login' ? next() : next('/login')
		}
		// redirect to frappe login page, for oauth and signup
		window.location.href = '/login'
		return next(false)
	}

	if (!session.isAuthorized && to.name !== 'No Permission') {
		return next('/no-permission')
	}
	if (session.isAuthorized && to.name === 'No Permission') {
		return next()
	}
	if (to.meta.isAllowed && !to.meta.isAllowed()) {
		return next('/no-permission')
	}

	const settings = settingsStore()
	if (!settings.initialized) {
		await settings.initialize()
	}
	// redirect to /setup if setup is not complete
	const setupComplete = settings.settings.setup_complete
	if (!setupComplete && to.name !== 'Setup') {
		return next('/setup')
	}
	// redirect to / if setup is complete and user is on /setup
	if (setupComplete && to.name === 'Setup') {
		return next('/')
	}

	to.path === '/login' ? next('/') : next()
})

router.afterEach((to, from) => {
	const TRACKED_RECORDS = ['Query', 'Dashboard', 'NotebookPage']
	const toName = to.name as string
	if (
		TRACKED_RECORDS.includes(toName) &&
		toName !== from.name &&
		to.params.name !== from.params.name
	) {
		sessionStore().createViewLog(toName, to.params.name as string)
	}
})

const _fetch = window.fetch
window.fetch = async function () {
	const res = await _fetch(...arguments)
	if (res.status === 403 && (!document.cookie || document.cookie.includes('user_id=Guest'))) {
		sessionStore().resetSession()
		router.push('/login')
	}
	return res
}

export default router
