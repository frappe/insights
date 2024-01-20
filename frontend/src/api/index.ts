import { call, createDocumentResource, createListResource, createResource } from 'frappe-ui'
import getWhitelistedMethods from './whitelistedMethods'

export const login = (email: string, password: string): Promise<User> => {
	return call('login', { usr: email, pwd: password })
}
export const logout = (): Promise<any> => call('logout')

export const fetchUserInfo = (): Promise<any> => call('insights.api.get_user_info')
export const trackActiveSite = (): Promise<any> => call('insights.api.telemetry.track_active_site')

export const createLastViewedLog = (recordType: string, recordName: string) => {
	return call('insights.api.home.create_last_viewed_log', {
		record_type: recordType,
		record_name: recordName,
	}) as Promise<any>
}

export const getListResource = (listResourceOption: ListResourceParams): ListResource => {
	return createListResource(listResourceOption)
}

export const createDataSource: Resource = createResource({ url: 'insights.api.setup.add_database' })
export const testDataSourceConnection: Resource = createResource({
	url: 'insights.api.setup.test_database_connection',
})

export const createQuery: Resource = createResource({ url: 'insights.api.queries.create_query' })

export const getDocumentResource = (
	doctype: string,
	docname?: string,
	options?: object
) => {
	const resource = createDocumentResource({
		doctype: doctype,
		name: docname || doctype,
		whitelistedMethods: getWhitelistedMethods(doctype),
		...options,
	})
	resource.fetchIfNeeded = async () => {
		if (!resource.get.loading) {
			await resource.get.fetch()
		}
	}
	return resource
}

export const fetchTableName = async (data_source: string, table: string) => {
	return call('insights.api.data_sources.get_table_name', {
		data_source: data_source,
		table: table,
	})
}