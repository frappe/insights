import { call, createResource } from 'frappe-ui'
import { ref } from 'vue'

const setupComplete = ref(localStorage.getItem('setupComplete') === 'true')

const getSetupStatus = async () => {
	if (localStorage.getItem('setupComplete')) {
		setupComplete.value = localStorage.getItem('setupComplete') === 'true'
		return setupComplete.value
	}

	const setup_complete = await call('insights.api.setup.setup_complete')
	localStorage.setItem('setupComplete', setup_complete)
	setupComplete.value = setup_complete

	return setupComplete.value
}

const testDatabaseConnection = createResource({
	url: 'insights.api.setup.test_database_connection',
})

const createDatabase = createResource({
	url: 'insights.api.setup.add_database',
})

export { setupComplete, getSetupStatus, createDatabase, testDatabaseConnection }
