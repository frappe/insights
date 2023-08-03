import { call } from 'frappe-ui'

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
