import dayjs from '../helpers/dayjs'
import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'

const basePath = 'insights.insights.doctype.insights_workbook.insights_workbook.'

export type WorkbookListItem = {
	title: string
	name: string
	owner: string
	creation: string
	modified: string
	created_from_now: string
	modified_from_now: string
}
const workbooks = ref<WorkbookListItem[]>([])

const loading = ref(false)
async function getWorkbooks() {
	loading.value = true
	workbooks.value = await call(basePath + 'get_workbooks')
	workbooks.value = workbooks.value.map((workbook: any) => ({
		...workbook,
		created_from_now: dayjs(workbook.creation).fromNow(),
		modified_from_now: dayjs(workbook.modified).fromNow(),
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
