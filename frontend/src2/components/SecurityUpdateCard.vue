<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { call, SidebarCard } from 'frappe-ui'
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
	<SidebarCard
		v-if="show && update"
		theme="amber"
		:title="__('Security issues')"
		:description="description"
		:action="action"
		dismissible
		@dismiss="dismissedVersion = update.available_version"
	/>
</template>
