import dayjs from '@/utils/dayjs'
import { createResource, call } from 'frappe-ui'
import { defineStore } from 'pinia'

const notebooks = createResource({
	url: 'insights.api.notebooks.get_notebooks',
	initialData: [],
	cache: 'notebookList',
	transform(data) {
		return data.map((notebook) => {
			notebook.created_from_now = dayjs(notebook.creation).fromNow()
			notebook.modified_from_now = dayjs(notebook.modified).fromNow()
			return notebook
		})
	},
})

export default defineStore('notebooks', {
	state: () => ({
		list: [],
		loading: false,
		creating: false,
		deleting: false,
	}),
	actions: {
		async reload() {
			this.loading = true
			this.list = await notebooks.fetch()
			this.loading = false
		},
		async createNotebook(title) {
			this.creating = true
			await call('insights.api.notebooks.create_notebook', { title })
			this.creating = false
			this.reload()
		},
		async createPage(notebook_name) {
			return call('insights.api.notebooks.create_notebook_page', {
				notebook: notebook_name,
			})
		},
	},
})
