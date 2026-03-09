<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { call } from 'frappe-ui'
import { X } from 'lucide-vue-next'
import { ref, watch } from 'vue'
import session from '../session'
import { createToast } from '../helpers/toasts'

const dismissed = useStorage('insights:demo-banner-dismissed', false)
const loading = ref(false)
const show = ref(false)

async function checkDemoData() {
	if (dismissed.value || !session.user.is_admin) return
	try {
		const hasDemoData = await call('insights.setup.setup_wizard.check_demo_data_exists')
		show.value = !hasDemoData
	} catch {
		show.value = false
	}
}

watch(
	() => session.initialized,
	(val) => val && checkDemoData(),
	{ immediate: true },
)

async function setupDemoData() {
	loading.value = true
	try {
		await call('insights.setup.setup_wizard.setup_demo_data')
		show.value = false
		createToast({
			title: 'Demo Data Ready',
			message: 'Sample data with workbook has been set up successfully',
			variant: 'success',
		})
	} catch {
		createToast({
			title: 'Setup Failed',
			message: 'Failed to setup demo data',
			variant: 'error',
		})
	} finally {
		loading.value = false
	}
}

function dismiss() {
	dismissed.value = true
	show.value = false
}
</script>

<template>
	<div
		v-if="show && session.user.is_admin"
		class="flex items-center justify-between gap-3 border-b px-4 py-2.5 text-sm"
	>
		<span class="text-gray-800">
			Get started quickly with sample data and a pre-built workbook.
		</span>
		<div class="flex items-center gap-2">
			<Button
				variant="solid"
				size="sm"
				label="Setup Demo Data"
				:loading="loading"
				@click="setupDemoData"
			/>
			<button v-if="!loading" class="rounded p-0.5 text-gray-600" @click="dismiss">
				<X class="h-4 w-4" />
			</button>
		</div>
	</div>
</template>
