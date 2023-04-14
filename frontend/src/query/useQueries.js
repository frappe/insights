import { safeJSONParse } from '@/utils'
import { API_METHODS } from '@/utils/query'
import { call, createDocumentResource, createResource } from 'frappe-ui'
import { defineStore } from 'pinia'

const queries = createResource({
	url: 'insights.api.get_queries',
	initialData: [],
	cache: 'queriesList',
})

export default defineStore('queries', {
	state: () => ({
		list: [],
		loading: false,
		creating: false,
		deleting: false,
	}),
	actions: {
		async reload() {
			this.loading = true
			this.list = await queries.fetch()
			this.loading = false
		},
		async create(data_source) {
			this.creating = true
			const queryName = await call('insights.api.create_query', { data_source })
			this.creating = false
			return queryName
		},
		filterByText(text) {
			if (!text) return this.list
			return this.list.filter((q) => {
				return (
					q.title.toLowerCase().includes(text.toLowerCase()) ||
					q.name.toLowerCase().includes(text.toLowerCase()) ||
					q.data_source.toLowerCase().includes(text.toLowerCase())
				)
			})
		},
	},
})

export function useQuery(name) {
	if (!name) return
	const query = createDocumentResource({
		doctype: 'Insights Query',
		name: name,
		whitelistedMethods: API_METHODS,
		transform(doc) {
			doc.columns = doc.columns.map((c) => {
				c.format_option = safeJSONParse(c.format_option, {})
				return c
			})
			doc.results = safeJSONParse(doc.results, [])
			query.resultColumns = doc.results[0]
			return doc
		},
	})
	query.get.fetch()
	return query
}
