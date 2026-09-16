<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { call } from 'frappe-ui'
import { TriangleAlert, X } from 'lucide-vue-next'
import { computed, ref, watchEffect } from 'vue'
import session from '../session'
import { __ } from '../translation'

type SecurityUpdate = {
	current_version: string
	available_version: string
	security_issues: number
	advisories_url: string
	frappe_cloud_url: string | null
}

const update = ref<SecurityUpdate | null>(null)
watchEffect(async () => {
	if (!session.user.is_admin) return
	update.value = await call('insights.api.get_security_update')
})

// per version, so the next release with fixes shows again
const dismissedVersion = useStorage('insights:security-update-dismissed', '')
const show = computed(
	() => update.value && update.value.available_version !== dismissedVersion.value,
)

const description = computed(() => {
	if (!update.value) return ''
	const { current_version, available_version, security_issues } = update.value
	return security_issues === 1
		? __(
				'Insights {0} has a known security issue, fixed in {1}.',
				current_version,
				available_version,
		  )
		: __(
				'Insights {0} has {1} known security issues, fixed in {2}.',
				current_version,
				String(security_issues),
				available_version,
		  )
})

const action = computed(() => {
	const url = update.value?.frappe_cloud_url || update.value?.advisories_url
	return {
		label: update.value?.frappe_cloud_url
			? __('Update from Frappe Cloud')
			: __('View Advisories'),
		onClick: () => {
			window.open(url, '_blank')
		},
	}
})
</script>

<template>
	<div
		v-if="show && update"
		class="flex flex-col gap-3 rounded-lg bg-white px-3 py-2.5 text-sm shadow-sm"
	>
		<div class="flex items-start justify-between gap-2">
			<div class="flex flex-col gap-1">
				<div class="flex items-center gap-1.5 font-medium text-p-base text-ink-gray-8">
					<TriangleAlert class="h-3.5 w-3.5 shrink-0 text-ink-amber-3" />
					{{ __('Security issues') }}
				</div>
				<div class="text-p-xs text-ink-gray-6">{{ description }}</div>
			</div>
			<Button
				class="shrink-0"
				variant="ghost"
				:icon="X"
				@click="dismissedVersion = update.available_version"
			/>
		</div>
		<Button :label="action.label" variant="subtle" @click="action.onClick" />
	</div>
</template>
