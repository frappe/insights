import dayjs from '@/utils/dayjs'
import { createResource } from 'frappe-ui'
import { defineStore } from 'pinia'

const sources = createResource({
	url: 'insights.api.get_data_sources',
	initialData: [],
	cache: 'sourceList',
	transform(data) {
		return data.map((source) => {
			source.created_from_now = dayjs(source.creation).fromNow()
			source.title = source.is_site_db ? window.location.hostname : source.name
			return source
		})
	},
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
