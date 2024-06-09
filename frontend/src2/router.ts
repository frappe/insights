import { createRouter, createWebHistory } from 'vue-router'
import session from './session.ts'

const routes = [
	{
		path: '/login',
		name: 'Login',
		component: () => import('@/pages/Login.vue'),
		meta: {
			isGuestView: true,
		},
	},
	{
		path: '/',
		name: 'Home',
		component: () => import('./home/Home.vue'),
	},
	{
		props: true,
		path: '/workbook/:name',
		name: 'Workbook',
		component: () => import('./workbook/Workbook.vue'),
	},
]

let router = createRouter({
	history: createWebHistory('/insights-v3'),
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
