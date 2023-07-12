import { call } from 'frappe-ui'
import { ref } from 'vue'

const setupComplete = ref(localStorage.getItem('setupComplete') === 'true')

async function loadSetupStatus() {
	if (!setupComplete.value) {
		const setup_status = await call('insights.api.setup.setup_complete')
		setupComplete.value = Boolean(setup_status)
	}
}
loadSetupStatus()

export async function isSetupComplete() {
	if (localStorage.getItem('setupComplete')) {
		setupComplete.value = localStorage.getItem('setupComplete') === 'true'
		return setupComplete.value
	}
	await loadSetupStatus()
	return setupComplete.value
}
export async function completeSetup() {
	await call('insights.api.setup.complete_setup')
	localStorage.setItem('setupComplete', true)
	window.location.reload()
}
