import { computed } from 'vue'
import { createDocumentResource } from 'frappe-ui'

export default class Query {
	constructor(id) {
		this.id = id
		this.resource = getQueryResource(id)
		this.docRef = computed(() => this.resource.doc)
	}

	get doc() {
		return this.docRef.value
	}
	get tables() {
		return this.doc.tables.map((table) => {
			return {
				...table,
				value: table.table,
				join: table.join ? JSON.parse(table.join) : null,
			}
		})
	}
	get dataSource() {
		return this.doc.data_source
	}

	setValue(key, value) {
		return this.resource.setValue.submit({ [key]: value })
	}

	run() {
		return this.resource.run.submit()
	}

	reset() {
		return this.resource.reset.submit()
	}

	delete() {
		return this.resource.delete.submit()
	}

	reload() {
		return this.resource.reload()
	}

	setLimit(limit) {
		if (parseInt(limit, 10) > 0) {
			return this.resource.set_limit.submit({ limit })
		}
	}
}

function getQueryResource(name) {
	const doctype = 'Query'
	const whitelistedMethods = [
		'run',
		'reset',
		'set_limit',
		'get_all_tables',
		'get_all_columns',
		'get_column_values',
		// table methods
		'add_table',
		'remove_table',
		'update_table',
		'get_join_options',
		// column methods
		'add_column',
		'move_column',
		'update_column',
		'remove_column',
		// filter methods
		'update_filters',
		// transform methods
		'apply_transform',
	].reduce((acc, method) => {
		acc[method] = method
		return acc
	}, {})

	return createDocumentResource({
		doctype,
		name,
		whitelistedMethods,
	})
}
