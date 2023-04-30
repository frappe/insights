import { watchDebounced } from '@vueuse/core'
import { createDocumentResource } from 'frappe-ui'
import { computed, reactive } from 'vue'
import jsBeautify from 'js-beautify'

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
			content: beautifyHTML(state.doc.content),
		})
		state.loading = false
	}

	const docChanged = computed(() =>
		JSON.parse(
			JSON.stringify({
				title: state.doc.title,
				content: state.doc.content,
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
		{ deep: true, debounce: 2000 }
	)

	return state
}

function beautifyHTML(html) {
	return jsBeautify.html(html, {
		indent_size: 2,
		indent_char: ' ',
		max_preserve_newlines: 1,
		preserve_newlines: true,
		keep_array_indentation: false,
		break_chained_methods: false,
		indent_scripts: 'normal',
		brace_style: 'collapse',
		space_before_conditional: true,
		unescape_strings: false,
		jslint_happy: false,
		end_with_newline: false,
		wrap_line_length: 0,
		indent_inner_html: false,
		comma_first: false,
		e4x: false,
		indent_empty_lines: false,
	})
}
