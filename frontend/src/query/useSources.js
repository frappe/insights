import { createResource } from 'frappe-ui'
import { defineStore } from 'pinia'

const sources = createResource({
	url: 'insights.api.get_data_sources',
	initialData: [],
	cache: 'sourceList',
})

export default defineStore('sources', {
	state: () => ({
		list: [],
		loading: false,
		creating: false,
		deleting: false,
	}),
	actions: {
		async reload() {
			this.loading = true
			this.list = await sources.fetch()
			this.loading = false
		},
	},
})
