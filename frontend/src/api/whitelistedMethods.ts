const whitelistedMethods = {
	'Insights Settings': {
		update_settings: 'update_settings',
		send_support_login_link: 'send_support_login_link',
	},
}
export default function getWhitelistedMethods(doctype: string) {
	return whitelistedMethods[doctype as keyof typeof whitelistedMethods] || {}
}
