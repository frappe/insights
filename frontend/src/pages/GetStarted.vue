<template>
	<div class="flex flex-1 flex-col rounded bg-gray-100 pb-8">
		<div class="flex flex-1 flex-col items-center justify-center">
			<div class="flex flex-col text-base">
				<div class="mb-2 text-2xl text-gray-600">Get Started</div>
				<router-link
					:to="step.to"
					v-for="step in onboardingSteps"
					class="mt-1 flex cursor-pointer items-center py-1.5 text-gray-600 hover:text-gray-700"
					@click="step.clickAction ? step.clickAction() : null"
				>
					<FeatherIcon
						:name="step.completed ? 'check-circle' : 'circle'"
						class="mr-2 h-4 w-4"
						:class="[step.completed ? 'text-green-600' : '']"
					/>
					<p>{{ step.label }}</p>
				</router-link>
			</div>
		</div>
		<div
			class="cursor-pointer text-center text-sm font-light text-gray-600 hover:underline"
			@click="openDialog = true"
		>
			Skip?
		</div>
	</div>

	<Dialog :options="{ title: 'Skip Onboarding' }" v-model="openDialog">
		<template #body-content>
			<p class="text-base text-gray-600">Are you sure you want to skip onboarding?</p>
		</template>
		<template #actions>
			<Button variant="danger" @click="skip"> Yes </Button>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { updateDocumentTitle } from '@/utils'
import {
	completedSteps,
	updateStep,
	updateOnboardingStatus,
	skipOnboarding,
} from '@/utils/onboarding'

updateOnboardingStatus()

const completionState = computed(() => completedSteps.value)
const onboardingSteps = ref([
	{
		label: 'Browse data',
		to: { name: 'DataSourceList' },
		completed: completionState.value.browseData,
		clickAction: () => updateStep('browseData', true),
	},
	{
		label: 'Create query',
		to: { name: 'QueryBuilder' },
		completed: completionState.value.createQuery,
	},
	{
		label: 'Create a chart',
		to: { name: 'QueryBuilder' },
		completed: completionState.value.createChart,
	},
	{
		label: 'Create dashboard',
		to: { name: 'Dashboards' },
		completed: completionState.value.createDashboard,
	},
	{
		label: 'Add to dashboard',
		to: { name: 'Dashboards' },
		completed: completionState.value.addChart,
	},
])

const openDialog = ref(false)
const skip = () => {
	skipOnboarding()
	openDialog.value = false
}

const pageMeta = ref({
	title: 'Get Started',
})
updateDocumentTitle(pageMeta)
</script>
