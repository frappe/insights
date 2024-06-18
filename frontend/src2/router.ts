import { createRouter, createWebHistory } from 'vue-router'
import session from './session.ts'

const routes = [
	{
		path: '/login',
		name: 'Login',
		component: () => import('@/pages/Login.vue'),
		meta: { isGuestView: true, hideSidebar: true },
	},
	{
		path: '/',
		name: 'Home',
		redirect: '/workbook',
		component: () => import('./home/Home.vue'),
	},
	{
		path: '/workbook',
		name: 'WorkbookList',
		component: () => import('./workbook/WorkbookList.vue'),
	},
	{
		props: true,
		name: 'Workbook',
		path: '/workbook/:name',
		component: () => import('./workbook/Workbook.vue'),
		redirect: (to: any) => `/workbook/${to.params.name}/query/0`,
		meta: { hideSidebar: true },
		children: [
			{
				props: true,
				path: 'query/:index',
				name: 'WorkbookQuery',
				component: () => import('./workbook/WorkbookQuery.vue'),
			},
			{
				props: true,
				path: 'chart/:index',
				name: 'WorkbookChart',
				component: () => import('./workbook/WorkbookChart.vue'),
			},
			{
				props: true,
				path: 'dashboard/:index',
				name: 'WorkbookDashboard',
				component: () => import('./workbook/WorkbookDashboard.vue'),
			},
		],
	},
	{
		path: '/:pathMatch(.*)*',
		component: () => import('@/pages/NotFound.vue'),
		meta: { hideSidebar: true },
	}
]

let router = createRouter({
	history: createWebHistory('/insights_v3'),
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
