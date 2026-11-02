import { call } from 'frappe-ui'
import { createRouter, createWebHistory, RouteLocationNormalized } from 'vue-router'
import { APP_PATH } from './app_path.ts'
import session from './session.ts'

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
		// a link to an old Insights template, such as ERPNext's old workspace banner
		path: '/template/:app/:folder',
		name: 'Template',
		component: () => import('./workbook/WorkbookList.vue'),
		beforeEnter: openTemplateWorkbook,
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

async function openTemplateWorkbook(to: RouteLocationNormalized) {
	const workbook = await call('insights.api.upgrade.get_template_workbook', {
		template: `${to.params.app}/${to.params.folder}`,
		// eslint-disable-next-line no-restricted-syntax -- an old link that resolves to nothing opens the workbooks list, where the user would look next
	}).catch(() => null)
	return workbook
		? { name: 'Workbook', params: { workbook_name: workbook } }
		: { name: 'WorkbookList' }
}

const READER_ROUTES = ['DashboardList', 'Dashboard', 'SharedChart', 'SharedDashboard']

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

	if (to.path === '/login') return next('/')

	// A user without an Insights role reads the dashboards they may open, and
	// nothing else. Every other page would call endpoints that refuse them
	if (!session.isAuthorized && !READER_ROUTES.includes(to.name as string)) {
		return next({ name: 'DashboardList' })
	}
	next()
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
