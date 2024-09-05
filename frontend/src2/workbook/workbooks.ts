import { useTimeAgo } from '@vueuse/core'
import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { WorkbookListItem } from '../types/workbook.types'

const workbooks = ref<WorkbookListItem[]>([])

const loading = ref(false)
async function getWorkbooks() {
	loading.value = true
	workbooks.value = await call('insights.api.workbooks.get_workbooks')
	workbooks.value = workbooks.value.map((workbook: any) => ({
		...workbook,
		created_from_now: useTimeAgo(workbook.creation),
		modified_from_now: useTimeAgo(workbook.modified),
	}))
	loading.value = false
	return workbooks.value
}

export default function useWorkbookListItemStore() {
	if (!workbooks.value.length) {
		getWorkbooks()
	}

	return reactive({
		workbooks,
		loading,
		getWorkbooks,
	})
}
