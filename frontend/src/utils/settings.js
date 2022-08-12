import { reactive } from 'vue'
import { createResource } from 'frappe-ui'

const updateUserDefaultResource = createResource('insights.api.update_user_default')
const getDefaultsResource = createResource('insights.api.get_user_defaults')

const settings = reactive({
	hide_sidebar: true,
	updating: false,
	fetch,
	update,
})

function update(key, value) {
	updateUserDefaultResource.submit({ key, value })
	settings.updating = updateUserDefaultResource.loading
}

function fetch() {
	getDefaultsResource.fetch(null, {
		onSuccess(res) {
			for (const key in res) {
				if (key == 'hide_sidebar') res[key] = res[key] == '1' ? true : false
				settings[key] = res[key]
			}
		},
	})
}

export default settings
