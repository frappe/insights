import { createResource, call } from 'frappe-ui'
import { reactive } from 'vue'

const subscription = reactive({
	trialExpired: null,
	fetchTrialStatus,
})

async function fetchTrialStatus() {
	subscription.trialExpired = await call('insights.api.subscription.trial_expired')
	return subscription.trialExpired
}

export async function getLoginLink() {
	return await call('insights.api.subscription.get_login_link')
}

export async function getTrialStatus() {
	if (import.meta.env.DEV) return false
	return subscription.trialExpired !== null ? subscription.trialExpired : await fetchTrialStatus()
}

export default subscription
