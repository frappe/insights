<template>
	<div
		class="flex h-[calc(100%)] min-h-[38rem] flex-col items-center justify-center rounded-md bg-gray-100 pb-12"
	>
		<div class="mb-4 text-2xl font-light text-gray-600">Get Started</div>
		<div class="flex flex-col space-y-3 text-base">
			<router-link
				:to="step.to"
				v-for="step in onboardingSteps"
				class="flex cursor-pointer items-center justify-center rounded border bg-gray-200 px-6 py-1.5 text-gray-600 hover:text-gray-700"
				@click="step.clickAction ? step.clickAction() : null"
			>
				<FeatherIcon
					:name="step.completed ? 'check-circle' : 'alert-circle'"
					class="mr-2 h-4 w-4"
					:class="[step.completed ? 'text-green-500' : '']"
				/>
				<p>{{ step.label }}</p>
			</router-link>
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { updateDocumentTitle } from '@/utils'
import { completedSteps, updateStep, updateOnboardingStatus } from '@/utils/onboarding'

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
		to: { name: 'QueryList' },
		completed: completionState.value.createQuery,
	},
	{
		label: 'Create dashboard',
		to: { name: 'DashboardList' },
		completed: completionState.value.createDashboard,
	},
	{
		label: 'Create visualization',
		to: { name: 'QueryList' },
		completed: completionState.value.createVisualization,
	},
	{
		label: 'Add visualization',
		to: { name: 'DashboardList' },
		completed: completedSteps.value.addVisualization,
	},
])

const pageMeta = ref({
	title: 'Get Started',
})
updateDocumentTitle(pageMeta)
</script>
