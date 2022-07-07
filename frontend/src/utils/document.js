import { watch, ref, reactive } from 'vue'

const updateDocumentTitle = (meta) => {
	watch(
		() => meta,
		(meta) => {
			if (!meta.value.title) return
			if (meta.value.title && meta.value.subtitle) {
				document.title = `${meta.value.title} | ${meta.value.subtitle}`
				return
			}
			if (meta.value.title) {
				document.title = `${meta.value.title} | Frappe Insights`
				return
			}
		},
		{ immediate: true, deep: true }
	)
}

export { updateDocumentTitle }
