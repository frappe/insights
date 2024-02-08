import { safeJSONParse } from '@/utils'
import { createDocumentResource } from 'frappe-ui'
import { computed, reactive } from 'vue'
import { getFormattedResult } from '@/utils/query/results'

export default function useQueryResults(result_name) {
	const resource = getResultResource(result_name)
	resource.get.fetch()
	return reactive({
		reload: () => resource.get.fetch(),
		loading: computed(() => resource.loading),
		data: computed(() => resource.doc?.results || []),
		columns: computed(() => resource.doc?.results?.[0] || []),
		formattedResults: computed(() => getFormattedResult(resource.doc?.results)),
	})
}

export function getResultResource(resultName) {
	return createDocumentResource({
		doctype: 'Insights Query Result',
		name: resultName,
		auto: false,
		transform: (doc) => {
			doc.results = safeJSONParse(doc.results, [])
			return doc
		},
	})
}
