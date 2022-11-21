import { createDocumentResource } from 'frappe-ui'

const resource = createDocumentResource({
	doctype: 'Insights Settings',
	name: 'Insights Settings',
	whitelistedMethods: { update_settings: 'update_settings' },
})
resource.get.fetch()
resource.updateSettings = (settings) => {
	resource.update_settings.submit({ settings })
}
export default resource
