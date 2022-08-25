import { call } from 'frappe-ui'
import { useStorage } from '@vueuse/core'
import { ref } from 'vue'

const onboardingComplete = ref(localStorage.getItem('onboardingComplete') === 'true')
const completedSteps = useStorage('insights:completedSteps', {
	browseData: false,
	createQuery: false,
	createVisualization: false,
	createDashboard: false,
	addVisualization: false,
})

const getOnboardingStatus = async () => {
	if (localStorage.getItem('onboardingComplete')) {
		onboardingComplete.value = localStorage.getItem('onboardingComplete') === 'true'
		return onboardingComplete.value
	}
	await updateOnboardingStatus()
	return onboardingComplete.value
}

async function updateOnboardingStatus() {
	const onboarding_status = await call('insights.api.get_onboarding_status')
	onboardingComplete.value = onboarding_status.is_onboarded
	updateSteps(onboarding_status)
}

function updateStep(step, completionStatus) {
	completedSteps.value[step] = completionStatus
}

function updateSteps(onboarding_status) {
	updateStep('createQuery', onboarding_status.query_created)
	updateStep('createVisualization', onboarding_status.visualization_created)
	updateStep('createDashboard', onboarding_status.dashboard_created)
	updateStep('addVisualization', onboarding_status.visualization_added)

	if (
		!onboarding_status.is_onboarded &&
		onboarding_status.query_created &&
		onboarding_status.visualization_created &&
		onboarding_status.dashboard_created &&
		onboarding_status.visualization_added
	) {
		skipOnboarding()
	}
}

async function skipOnboarding() {
	localStorage.setItem('onboardingComplete', true)
	await call('insights.api.skip_onboarding')
	onboardingComplete.value = true
	updateOnboardingStatus()
}

export {
	onboardingComplete,
	completedSteps,
	getOnboardingStatus,
	updateOnboardingStatus,
	skipOnboarding,
	updateStep,
}
