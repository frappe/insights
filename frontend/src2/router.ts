import { call } from 'frappe-ui'
import { createRouter, createWebHistory, RouteLocation } from 'vue-router'
import { APP_PATH } from './app_path.ts'
import session from './session.ts'

// A v2 chart or dashboard keeps its old name in `old_name`, and a link written
// then still carries it. Resolving in the guard puts the current name in the
// URL and lets the page take its name as a plain prop.
function resolveRenamed(method: string, argument: string, param: string) {
	return async (to: RouteLocation) => {
		const old = String(to.params[param])
		const current = await call(method, { [argument]: old })
		if (!current || current === old) return true
		return {
			name: to.name as string,
			params: { ...to.params, [param]: current },
			query: to.query,
			hash: to.hash,
			replace: true,
		}
	}
}

const routes = [
	{
		path: '/login',
		name: 'Login',
		component: () => import('./auth/Login.vue'),
		meta: { isGuestView: true, hideSidebar: true },
	},
	{
		path: '/',
		name: 'Home',
		redirect: '/dashboards',
		component: () => import('./home/Home.vue'),
	},
	{
		path: '/dashboards',
		name: 'DashboardList',
		component: () => import('./dashboard/DashboardList.vue'),
	},
	{
		props: true,
		name: 'Dashboard',
		path: '/dashboards/:name',
		component: () => import('./dashboard/Dashboard.vue'),
		beforeEnter: resolveRenamed(
			'insights.api.shared.get_dashboard_name',
			'dashboard_name',
			'name',
		),
	},
	{
		path: '/workbook',
		name: 'WorkbookList',
		component: () => import('./workbook/WorkbookList.vue'),
	},
	{
		props: true,
		name: 'Workbook',
		path: '/workbook/:workbook_name',
		component: () => import('./workbook/Workbook.vue'),
		meta: { hideSidebar: true },
		children: [
			{
				props: true,
				path: 'query/:query_name',
				name: 'WorkbookQuery',
				component: () => import('./workbook/WorkbookQuery.vue'),
			},
			{
				props: true,
				path: 'chart/:chart_name',
				name: 'WorkbookChart',
				component: () => import('./workbook/WorkbookChart.vue'),
			},
			{
				props: true,
				path: 'dashboard/:dashboard_name',
				name: 'WorkbookDashboard',
				component: () => import('./workbook/WorkbookDashboard.vue'),
			},
		],
	},
	{
		props: true,
		name: 'OpenTemplate',
		path: '/template/:app/:folder',
		component: () => import('./workbook/OpenTemplate.vue'),
		meta: { hideSidebar: true },
	},
	{
		path: '/data-source',
		name: 'DataSourceList',
		component: () => import('./data_source/DataSourceList.vue'),
	},
	{
		props: true,
		path: '/data-source/:name',
		name: 'DataSourceTableList',
		component: () => import('./data_source/DataSourceTableList.vue'),
	},
	{
		props: true,
		path: '/data-source/:data_source/:table_name',
		name: 'DataSourceTable',
		component: () => import('./data_source/DataSourceTable.vue'),
	},
	{
		path: '/data-store',
		name: 'DataStoreList',
		component: () => import('./data_store/DataStoreList.vue'),
	},
	{
		props: true,
		name: 'SharedChart',
		path: '/shared/chart/:chart_name',
		component: () => import('./charts/SharedChart.vue'),
		beforeEnter: resolveRenamed(
			'insights.api.shared.get_chart_name',
			'chart_name',
			'chart_name',
		),
		meta: {
			hideSidebar: true,
			isGuestView: true,
		},
	},
	{
		props: true,
		name: 'SharedDashboard',
		path: '/shared/dashboard/:dashboard_name',
		component: () => import('./dashboard/SharedDashboard.vue'),
		beforeEnter: resolveRenamed(
			'insights.api.shared.get_dashboard_name',
			'dashboard_name',
			'dashboard_name',
		),
		meta: {
			hideSidebar: true,
			isGuestView: true,
		},
	},
	{
		path: '/:pathMatch(.*)*',
		component: () => import('./auth/NotFound.vue'),
		meta: { hideSidebar: true },
	},
]

let router = createRouter({
	history: createWebHistory(APP_PATH),
	// @ts-ignore
	routes,
})

router.beforeEach(async (to, _, next) => {
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

	to.path === '/login' ? next('/') : next()
})

const _fetch = window.fetch
window.fetch = async function () {
	// @ts-ignore
	const res = await _fetch(...arguments)
	if (res.status === 403 && (!document.cookie || document.cookie.includes('user_id=Guest'))) {
		session.resetSession()
		router.push('/login')
	}
	return res
}

export default router
