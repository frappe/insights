import { call, createResource } from 'frappe-ui'
import { ref } from 'vue'

const setupComplete = ref(localStorage.getItem('setupComplete') === 'true')

const getSetupStatus = async () => {
	if (localStorage.getItem('setupComplete')) {
		setupComplete.value = localStorage.getItem('setupComplete') === 'true'
		return setupComplete.value
	}

	const is_onboarded = await call('insights.api.setup.setup_complete')
	localStorage.setItem('setupComplete', is_onboarded)
	setupComplete.value = is_onboarded

	return setupComplete.value
}

const testDatabaseConnection = createResource({
	method: 'insights.api.setup.test_database_connection',
})

const createDatabase = createResource({
	method: 'insights.api.setup.add_database',
	onSuccess() {
		localStorage.removeItem('setupComplete')
		getSetupStatus()
	},
})

export { setupComplete, getSetupStatus, createDatabase, testDatabaseConnection }
