import router from '@/router'
import { __ } from '../translation'
import { useTimeAgo } from '@vueuse/core'
import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { confirmDialog } from '../helpers/confirm_dialog'
import { createToast } from '../helpers/toasts'
import { WorkbookListItem } from '../types/workbook.types'

const workbooks = ref<WorkbookListItem[]>([])

const loading = ref(false)
async function getWorkbooks(
	search_term?: string,
	limit: number = 100,
	scope?: 'all' | 'owned' | 'shared',
	folder?: string | null,
) {
	loading.value = true
	const result = await call('insights.api.workbooks.get_workbooks', {
		search_term,
		limit,
		scope: scope === 'all' ? null : scope,
		folder: folder ?? null,
	})
	workbooks.value = result.map((workbook: any) => ({
		...workbook,
		created_from_now: useTimeAgo(workbook.creation),
		modified_from_now: useTimeAgo(workbook.modified),
	}))
	loading.value = false
	return workbooks.value
}

function importWorkbook(workbook: any) {
	confirmDialog({
		title: __('Import Workbook'),
		message: __('Are you sure you want to import this workbook?'),
		onSuccess: () => {
			call('insights.api.workbooks.import_workbook', { workbook }).then((name: string) => {
				getWorkbooks().then(() => {
					createToast({
						message: __('Workbook imported successfully'),
						variant: 'success',
					})
				})
				router.push(`/workbook/${name}`)
			})
		},
	})
}

export default function useWorkbookListItemStore() {
	// the list view drives fetching (with folder/scope); no implicit fetch here,
	// otherwise an unscoped "fetch all" can race with and overwrite it
	return reactive({
		workbooks,
		loading,
		getWorkbooks,
		importWorkbook,
	})
}
