import { createDocumentResource } from 'frappe-ui'
import { createToast } from '@/utils/toasts'

const resource = createDocumentResource({
	doctype: 'Insights Settings',
	name: 'Insights Settings',
	whitelistedMethods: { update_settings: 'update_settings' },
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
