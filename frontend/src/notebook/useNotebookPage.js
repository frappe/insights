import { useAutoSave } from '@/utils'
import { createDocumentResource } from 'frappe-ui'
import { computed, reactive } from 'vue'

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
		state.loading = false
	}
	state.reload()

	state.save = async () => {
		state.loading = true
		await resource.setValue.submit({
			title: state.doc.title,
			content: state.doc.content,
		})
		state.loading = false
	}

	const fieldsToWatch = computed(() => {
		// if doc is not loaded, don't watch
		if (!state.doc.name) return
		return {
			title: state.doc.title,
			content: state.doc.content,
		}
	})
	useAutoSave(fieldsToWatch, {
		saveFn: state.save,
		interval: 1500,
	})

	return state
}
