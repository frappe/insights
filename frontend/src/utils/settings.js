import { createToast } from '@/utils/toasts'
import { createDocumentResource } from 'frappe-ui'

const resource = createDocumentResource({
	doctype: 'Insights Settings',
	name: 'Insights Settings',
	auto: false,
	whitelistedMethods: {
		update_settings: 'update_settings',
		send_support_login_link: 'send_support_login_link',
	},
})
resource.updateSettings = (settings) => {
	resource.setValue.submit({ ...settings }).then(() => {
		createToast({
			title: 'Settings Updated',
			message: 'Your settings have been updated successfully',
			variant: 'success',
		})
	})
}
export default resource
