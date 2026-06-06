import { useTimeAgo } from '@vueuse/core'
import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { createInfoToast, createSuccessToast } from '../helpers/toasts'
import { showErrorToast } from '../helpers'

export type DashboardListItem = {
	name: string
	title: string
	workbook: string
	charts: number
	creation: string
	modified: string
	created_from_now: string
	modified_from_now: string
	preview_image: string
	views: number
	is_favourite: boolean
	folder?: string | null
}

export type DashboardFolder = {
	name: string
	title: string
	sort_order: number
}

const dashboards = ref<DashboardListItem[]>([])
const favorites = ref<DashboardListItem[]>([])
const folders = ref<DashboardFolder[]>([])

const loading = ref(false)
const mapTimeAgo = (dashboard: any) => ({
	...dashboard,
	created_from_now: useTimeAgo(dashboard.creation),
	modified_from_now: useTimeAgo(dashboard.modified),
})
async function fetchDashboards(search_term?: string, limit: number = 0) {
	loading.value = true

	const [regular, fav, dashboardFolders] = await Promise.all([
		call('insights.api.dashboards.get_dashboards', { search_term, limit }),
		call('insights.api.dashboards.get_dashboards', { get_favorites: true }),
		call('insights.api.dashboards.get_dashboard_folders'),
	])

	dashboards.value = regular.map(mapTimeAgo)
	favorites.value = fav.map(mapTimeAgo)
	folders.value = dashboardFolders
	loading.value = false
}

const updatingPreviewImage = ref<Record<string, boolean>>({})
async function updatePreviewImage(dashboard_name: string) {
	updatingPreviewImage.value[dashboard_name] = true
	createInfoToast('Updating preview image...')
	return call('insights.api.dashboards.update_dashboard_preview', { dashboard_name })
		.then((file_url: string) => {
			createSuccessToast('Preview image updated successfully')
			const dashboard = dashboards.value.find((d) => d.name === dashboard_name)
			if (dashboard) {
				dashboard.preview_image = file_url
			}
		})
		.catch(showErrorToast)
		.finally(() => {
			updatingPreviewImage.value[dashboard_name] = false
		})
}

async function toggleLike(dashboard_name: string, add: boolean) {
	return call('frappe.desk.like.toggle_like', {
		doctype: 'Insights Dashboard v3',
		name: dashboard_name,
		add: add ? 'Yes' : 'No',
	}).then(() => fetchDashboards())
}

async function createFolder(title: string) {
	await call('insights.api.dashboards.create_dashboard_folder', { title }).catch(showErrorToast)
	return fetchDashboards()
}

async function renameFolder(folder_name: string, title: string) {
	await call('insights.api.dashboards.rename_dashboard_folder', { folder_name, title }).catch(
		showErrorToast,
	)
	return fetchDashboards()
}

async function deleteFolder(folder_name: string) {
	await call('insights.api.dashboards.delete_dashboard_folder', { folder_name }).catch(
		showErrorToast,
	)
	return fetchDashboards()
}

async function moveDashboard(dashboard_name: string, folder_name?: string | null) {
	await call('insights.api.dashboards.move_dashboard_to_folder', {
		dashboard_name,
		folder_name: folder_name || null,
	}).catch(showErrorToast)
	return fetchDashboards()
}

async function updateFolderOrder(folder_names: string[]) {
	await call('insights.api.dashboards.update_dashboard_folder_order', { folder_names }).catch(
		showErrorToast,
	)
	return fetchDashboards()
}

export default function useDashboardStore() {
	if (!dashboards.value.length) {
		fetchDashboards()
	}

	return reactive({
		dashboards,
		favorites,
		folders,
		loading,
		fetchDashboards,

		updatePreviewImage,
		updatingPreviewImage,

		toggleLike,
		createFolder,
		renameFolder,
		deleteFolder,
		moveDashboard,
		updateFolderOrder,
	})
}
