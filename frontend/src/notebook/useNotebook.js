import dayjs from '@/utils/dayjs'
import { call, createDocumentResource } from 'frappe-ui'
import { reactive } from 'vue'

export default function useNotebook(name) {
	if (!name) throw new Error('Notebook name is required')
	const resource = createDocumentResource({
		doctype: 'Insights Notebook',
		name: name,
	})
	const state = reactive({
		doc: {},
		pages: [],
		loading: false,
	})

	state.reload = async () => {
		state.loading = true
		state.doc = await resource.get.fetch()
		state.pages = await call('insights.api.notebooks.get_notebook_pages', {
			notebook: name,
		})
		state.pages = state.pages.map((page) => {
			page.created_from_now = dayjs(page.creation).fromNow()
			page.modified_from_now = dayjs(page.modified).fromNow()
			return page
		})
		state.loading = false
	}
	state.reload()

	state.createPage = async () => {
		return call('insights.api.notebooks.create_notebook_page', {
			notebook: name,
		})
	}

	state.deleteNotebook = async () => {
		state.deleting = true
		await resource.delete.submit()
		state.deleting = false
	}

	return state
}
