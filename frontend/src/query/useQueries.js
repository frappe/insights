import { safeJSONParse } from '@/utils'
import { API_METHODS } from '@/utils/query'
import { call, createDocumentResource, createResource } from 'frappe-ui'
import { defineStore } from 'pinia'
import dayjs from '@/utils/dayjs'

const queries = createResource({
	url: 'insights.api.get_queries',
	initialData: [],
	cache: 'queriesList',
	transform(data) {
		return data.map((source) => {
			source.created_from_now = dayjs(source.creation).fromNow()
			Object.keys(source).forEach((key) => {
				if (!source[key]) source[key] = '-'
			})
			return source
		})
	},
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
		async create(data_source, title) {
			this.creating = true
			const queryName = await call('insights.api.create_query', { data_source, title })
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
