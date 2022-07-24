import { call, createResource } from 'frappe-ui'
import { ref } from 'vue'

const isOnboarded = ref(localStorage.getItem('isOnboarded') === 'true')

const getOnboardingStatus = async () => {
	if (localStorage.getItem('isOnboarded')) {
		isOnboarded.value = localStorage.getItem('isOnboarded') === 'true'
		return isOnboarded.value
	}

	const is_onboarded = await call('insights.api.onboarding.is_onboarded')
	localStorage.setItem('isOnboarded', is_onboarded)
	isOnboarded.value = is_onboarded

	return isOnboarded.value
}

const testDatabaseConnection = createResource({
	method: 'insights.api.onboarding.test_database_connection',
})

const createDatabase = createResource({
	method: 'insights.api.onboarding.add_database',
	onSuccess() {
		localStorage.removeItem('isOnboarded')
		getOnboardingStatus()
	},
})

export { isOnboarded, getOnboardingStatus, createDatabase, testDatabaseConnection }
