import { createDocumentResource } from 'frappe-ui'

const resource = createDocumentResource({
	doctype: 'System Settings',
	name: 'System Settings',
	auto: false,
})

export default resource
