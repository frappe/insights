<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { Sparkles } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import session from '../session'
import { __ } from '../translation'
import { setupDemoData as runDemoSetup } from './demo_data'

const dismissed = useStorage('insights:demo-banner-dismissed', false)
const loading = ref(false)
const show = computed(
	() =>
		session.initialized &&
		!dismissed.value &&
		session.user.is_admin &&
		!session.user.has_demo_data &&
		!session.user.has_workbooks,
)

async function setupDemoData() {
	loading.value = true
	await runDemoSetup().finally(() => (loading.value = false))
}

function dismiss() {
	dismissed.value = true
}
</script>

<template>
	<div
		v-if="show"
		class="flex flex-col gap-3 rounded-6 bg-surface-base px-3 py-2.5 text-sm shadow-sm"
	>
		<div class="flex items-start justify-between">
			<div class="flex flex-col gap-1">
				<div class="text-p-base-medium text-ink-gray-8">{{ __('Try demo data') }}</div>
				<div class="text-p-xs text-ink-gray-5">
					Explore with sample data and a pre-built workbook
				</div>
			</div>
			<Button
				v-if="!loading"
				class="mt-0.5 shrink-0"
				variant="ghost"
				icon="lucide-x"
				@click="dismiss"
			/>
		</div>
		<Button
			:label="__('Setup Demo Data')"
			variant="subtle"
			:loading="loading"
			@click="setupDemoData"
		>
			<template #prefix>
				<Sparkles class="h-3.5 w-3.5" />
			</template>
		</Button>
	</div>
</template>
