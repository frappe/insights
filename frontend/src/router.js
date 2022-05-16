import { createRouter, createWebHistory } from 'vue-router'

const routes = [
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
		path: '/query/:query_id',
		component: () => import('@/pages/Query.vue'),
		props: true,
	},
	{
		path: '/reports',
		name: 'Reports',
		component: () => import('@/pages/Reports.vue'),
	},
	{
		path: '/settings',
		name: 'Settings',
		component: () => import('@/pages/Settings.vue'),
	},
]

let router = createRouter({
	history: createWebHistory('/analytics'),
	routes,
})

router.beforeEach((to, from, next) => {
	const is_logged_in = !document.cookie.includes('user_id=Guest')

	if (is_logged_in) {
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
