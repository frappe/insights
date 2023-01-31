import { createToast } from '@/utils/toasts'
import { createDocumentResource } from 'frappe-ui'

const resource = createDocumentResource({
	doctype: 'Insights Settings',
	name: 'Insights Settings',
	whitelistedMethods: {
		update_settings: 'update_settings',
		send_support_login_link: 'send_support_login_link',
	},
})
resource.get.fetch()
resource.updateSettings = (settings) => {
	resource.update_settings.submit({ settings }).then(() => {
		createToast({
			title: 'Settings Updated',
			message: 'Your settings have been updated successfully',
			appearance: 'success',
		})
	})
}
export default resource
