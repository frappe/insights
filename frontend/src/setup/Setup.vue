<script setup>
import settingsStore from '@/stores/settingsStore'
import { computed, markRaw, provide, reactive, ref } from 'vue'
import SetupQuestions from './SetupQuestions.vue'
import SourceConnectionStep from './SourceConnectionStep.vue'
import SourceTypeStep from './SourceTypeStep.vue'
import { useRouter } from 'vue-router'

const setupState = reactive({
	sourceType: null, // 'erpnext', 'mariadb', 'postgresql', 'file', 'sample'
})
provide('setupState', setupState)

const titleBySourceType = {
	erpnext: 'Setup ERPNext',
	mariadb: 'Setup MariaDB',
	postgresql: 'Setup PostgreSQL',
	file: 'Setup Spreadsheet',
	sample: 'Select Sample Dataset',
}
const descriptionBySourceType = {
	erpnext:
		'Insights is already connected to your ERPNext site. You can optionally give a title to your site to help you identify it as a data source.',
	mariadb:
		'You need to enter your MariaDB database details to connect to your database. If you are not sure about your database details, please contact your database administrator.',
	postgresql:
		'You need to enter your PostgreSQL database details to connect to your database. If you are not sure about your database details, please contact your database administrator.',
	file: 'You need to upload a spreadsheet to connect to your data. Insights supports only .csv files.',
	sample: 'You can choose from one of the sample datasets to connect to Insights.',
}

const connectStepTitle = computed(() => {
	return titleBySourceType[setupState.sourceType] || 'Connect to Data'
})
const connectStepDescription = computed(() => {
	return descriptionBySourceType[setupState.sourceType]
})

const steps = ref([
	{
		title: 'Welcome to Insights',
		description: `
			To get started, you need to connect some data. You can connect to ERPNext, a SQL database, a spreadsheet, or you can explore our sample datasets to get a feel for how Insights works.
		`,
		component: markRaw(SourceTypeStep),
	},
	{
		title: connectStepTitle,
		description: connectStepDescription,
		component: markRaw(SourceConnectionStep),
	},
	{
		title: 'Help Us Improve',
		description: `
			Insights is under active development so	we’d like to ask you a few questions that will help us improve your experience in the future.
		`,
		component: markRaw(SetupQuestions),
	},
])

const currentStep = ref(0)
const settings = settingsStore()
const router = useRouter()
async function handleNext() {
	if (currentStep.value === steps.value.length - 1) {
		settings.settings.setup_complete = 1
		await settings.update({ setup_complete: 1 }, false)
		router.replace({ path: '/' })
		return
	}
	currentStep.value += 1
}

function handlePrev() {
	if (currentStep.value === 0) {
		return
	}
	currentStep.value -= 1
}
</script>

<template>
	<div class="flex h-full w-full bg-white pt-[7rem] text-lg">
		<div class="mx-auto flex w-[40rem] flex-col overflow-hidden">
			<div class="mx-auto w-fit">
				<div class="flex items-center space-x-2 py-1">
					<template v-for="(step, index) in steps">
						<div
							class="flex h-3 w-3 cursor-default items-center justify-center rounded-full transition-all"
							:class="[
								currentStep < index ? 'bg-gray-200' : 'bg-gray-800',
								currentStep === index ? 'ring-4 ring-gray-400' : '',
							]"
						></div>
						<div
							v-if="index !== steps.length - 1"
							class="w-7 border-b transition-all"
							:class="currentStep - 1 < index ? 'border-gray-400' : 'border-gray-800'"
						></div>
					</template>
				</div>
			</div>

			<div class="mt-8">
				<div class="text-3xl font-bold leading-9 text-gray-900">
					{{ steps[currentStep].title }}
				</div>
				<div class="text-base leading-5 text-gray-700">
					{{ steps[currentStep].description }}
				</div>
			</div>

			<div class="relative flex flex-col overflow-hidden">
				<transition name="fade" mode="out-in">
					<component
						:is="steps[currentStep].component"
						@next="handleNext"
						@prev="handlePrev"
					/>
				</transition>
				<div class="absolute bottom-0 left-0">
					<Button variant="outline" @click="handlePrev" v-if="currentStep > 0">
						Back
					</Button>
				</div>
			</div>
		</div>
	</div>
</template>
