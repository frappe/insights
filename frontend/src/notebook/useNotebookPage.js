import { safeJSONParse } from '@/utils'
import { watchDebounced } from '@vueuse/core'
import { createDocumentResource } from 'frappe-ui'
import { computed, reactive } from 'vue'

export default function useNotebookPage(page_name) {
	const resource = createDocumentResource({
		doctype: 'Insights Notebook Page',
		name: page_name,
		transform(doc) {
			doc.items = safeJSONParse(doc.dev_items, [])
			return doc
		},
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
			dev_items: JSON.stringify(state.doc.items, null, 2),
		})
		await state.reload()
		state.loading = false
	}

	const docChanged = computed(() =>
		JSON.parse(
			JSON.stringify({
				title: state.doc.title,
				items: state.doc.items,
			})
		)
	)
	watchDebounced(
		docChanged,
		(newState, oldState) => {
			if (!oldState.title) return
			if (JSON.stringify(newState) !== JSON.stringify(oldState)) {
				state.save()
			}
		},
		{ deep: true, debounce: 500 }
	)

	return state
}
