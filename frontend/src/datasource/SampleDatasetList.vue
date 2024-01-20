<script setup>
import sessionStore from '@/stores/sessionStore'
import { call } from 'frappe-ui'
import { inject, ref } from 'vue'

const emit = defineEmits(['submit'])
const selectedDataset = ref(null)
const sampleDatasets = [
	{
		name: 'ecommerce',
		title: 'eCommerce',
		description: 'An eCommerce dataset with orders, products, customers, and suppliers data.',
		icon: 'shopping-cart',
	},
]

const $notify = inject('$notify')
const settingUpSampleData = ref(false)
async function setupSampleData() {
	if (selectedDataset.value === null) {
		$notify({
			title: 'Please select a dataset',
			message: 'Please select a dataset to continue',
			type: 'error',
		})
		return
	}
	settingUpSampleData.value = true
	await call('insights.api.setup.setup_sample_data', {
		dataset: sampleDatasets[selectedDataset.value].name,
	})
	settingUpSampleData.value = false
	emit('submit')
}

const session = sessionStore()
const $socket = inject('$socket')
const progressLabel = ref('Continue')
$socket.on('insights_demo_setup_progress', (data) => {
	if (data.user == session.user.user_id) {
		progressLabel.value = `${data.progress.toFixed(0)}% complete...`
		if (data.progress == 100) {
			progressLabel.value = 'Continue'
		}
	}
})
</script>

<template>
	<div class="grid grid-cols-1 gap-4">
		<div
			v-for="(dataset, index) in sampleDatasets"
			class="col-span-1 flex cursor-pointer items-center rounded border border-gray-300 px-4 py-3 transition-all"
			:class="selectedDataset === index ? 'border-gray-600' : 'hover:border-gray-300'"
			@click="selectedDataset = index"
		>
			<div v-if="dataset.icon" class="mr-3 p-2 text-gray-600">
				<FeatherIcon :name="dataset.icon" class="h-8 w-8" />
			</div>
			<div>
				<div class="font-bold text-gray-900">
					{{ dataset.title }}
				</div>
				<div class="text-base text-gray-700">{{ dataset.description }}</div>
			</div>
		</div>
	</div>

	<div class="mt-6 flex flex-shrink-0 justify-end space-x-3">
		<Button
			variant="solid"
			@click="setupSampleData"
			:loading="settingUpSampleData"
			:disabled="settingUpSampleData || selectedDataset === null"
		>
			{{ progressLabel }}
		</Button>
	</div>
</template>
