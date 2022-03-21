import { createRouter, createWebHistory } from 'vue-router'

const routes = [
	{
		path: '/',
		name: 'Dashboards',
		component: () => import('@/pages/Dashboards.vue'),
	},
	{
		path: '/query',
		name: 'QueryList',
		component: () => import('@/pages/QueryList.vue'),
	},
	{
		name: 'Builder',
		path: '/query/:query_id',
		component: () => import('@/pages/Builder.vue'),
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

export default router
