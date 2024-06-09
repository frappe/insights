const whitelistedMethods = {
	'Insights Settings': {
		update_settings: 'update_settings',
	},
	'Insights Data Source': {
		enqueue_sync_tables: 'enqueue_sync_tables',
		get_tables: 'get_tables',
		get_queries: 'get_queries',
		update_table_link: 'update_table_link',
		delete_table_link: 'delete_table_link',
	},
	'Insights Table': {
		syncTable: 'sync_table',
		updateVisibility: 'update_visibility',
		getPreview: 'get_preview',
		update_column_type: 'update_column_type',
	},
}
export default function getWhitelistedMethods(doctype: string) {
	return whitelistedMethods[doctype as keyof typeof whitelistedMethods] || {}
}
