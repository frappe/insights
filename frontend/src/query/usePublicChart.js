import { safeJSONParse } from '@/utils'
import { getFormattedResult } from '@/utils/query/results'
import { convertResultToObjects } from '@/widgets/useChartData'
import { createResource } from 'frappe-ui'
import { reactive } from 'vue'

export default function usePublicChart(publicKey) {
	const resource = getPublicChart(publicKey)
	const state = reactive({
		query: null,
		data: [],
		loading: false,
		error: null,
		doc: {
			doctype: 'Insights Chart',
			name: undefined,
			chart_type: undefined,
			options: {},
			is_public: false,
		},
	})

	async function load() {
		state.loading = true
		state.doc = await resource.fetch()
		const results = getFormattedResult(state.doc.data)
		state.data = convertResultToObjects(results)
		state.loading = false
	}
	load()

	return Object.assign(state, {
		load,
	})
}

function getPublicChart(public_key) {
	return createResource({
		url: 'insights.api.public.get_public_chart',
		params: { public_key },
		transform(doc) {
			doc.options = safeJSONParse(doc.options)
			doc.data = safeJSONParse(doc.data)
			return doc
		},
	})
}
