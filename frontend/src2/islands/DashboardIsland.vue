<script setup lang="ts">
import { ref, watchEffect } from 'vue'
import DashboardBody from '../dashboard/DashboardBody.vue'
import DashboardItemView from '../dashboard/DashboardItemView.vue'
import StaticGridLayout from '../dashboard/StaticGridLayout.vue'
import { useDashboardView, type DashboardAction } from '../dashboard/view'
import { placedDashboard, type DashboardPlacement } from './placement'

// A dashboard inside a host page. The island renders the dashboard body only,
// with no header. It emits what a header needs instead: the title and the
// dashboard's actions. The host renders its own header from them.
//
// Both are plain events, not `update:` models. The host never sets either one,
// so there is no prop to write back to.
const props = defineProps<DashboardPlacement>()

const emit = defineEmits<{
	title: [title: string | null]
	actions: [actions: DashboardAction[]]
}>()

const shown = useDashboardView(() => placedDashboard(props), 'desk')

const body = ref<InstanceType<typeof DashboardBody>>()

// There is no title while the dashboard loads or when it is Not Found. The host
// then keeps its current page title.
watchEffect(() => emit('title', shown.title || null))

// No actions while the dashboard loads or when it is Not Found. Emit a new array
// each time: the host runs its own copy of Vue and cannot track our reactive
// objects. An action with an `href` already holds the absolute Insights URL
// that the island's router resolved.
watchEffect(() => {
	const instance = body.value
	if (!instance || shown.loading || shown.notFound) return emit('actions', [])
	emit(
		'actions',
		instance.actions.map((action: DashboardAction) => ({ ...action })),
	)
})
</script>

<template>
	<DashboardBody
		ref="body"
		:dashboard="shown"
		:grid="StaticGridLayout"
		:cell="DashboardItemView"
	/>
</template>
