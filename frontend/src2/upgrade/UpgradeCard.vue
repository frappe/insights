<script setup lang="ts">
import { SidebarCard } from 'frappe-ui'
import { computed } from 'vue'
import session from '../session'
import { __ } from '../translation'
import upgrade from './upgrade'

const count = computed(() => session.user.upgrade_item_count)
const description = computed(() =>
	count.value === 1
		? __('1 item needs attention after the upgrade.')
		: __('{0} items need attention after the upgrade.', String(count.value)),
)
const action = {
	label: __('Review'),
	onClick: () => upgrade.open('attention'),
}
</script>

<template>
	<SidebarCard
		v-if="count"
		theme="blue"
		:title="__('Insights 4')"
		:description="description"
		:action="action"
	/>
</template>
