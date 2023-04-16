import { createDocumentResource } from 'frappe-ui'
import { reactive } from 'vue'

export default function useNotebookPage(page_name) {
	const resource = createDocumentResource({
		doctype: 'Insights Notebook Page',
		name: page_name,
	})
	const state = reactive({
		doc: {},
		loading: false,
	})

	state.reload = async () => {
		state.loading = true
		state.doc = await resource.get.fetch()
		state.doc.items = []
		state.loading = false
	}
	state.reload()

	return state
}
