<script setup lang="ts">
import { ref, watchEffect } from 'vue'
import DashboardBody from '../dashboard/DashboardBody.vue'
import DashboardItemView from '../dashboard/DashboardItemView.vue'
import StaticGridLayout from '../dashboard/StaticGridLayout.vue'
import { useDashboardView, type DashboardAction } from '../dashboard/view'
import { placedDashboard, type DashboardPlacement } from './placement'

// A dashboard inside another app. The island is the dashboard body and nothing
// else: it draws no header, and reports what a header would say — the title, and
// the actions that belong to the dashboard on screen. Every host has a header of
// its own already, and draws it from what arrives here.
//
// Both are plain events, not `update:` models. A host never sets either one, so
// there is no prop here to write back to.
const props = defineProps<DashboardPlacement>()

const emit = defineEmits<{
	title: [title: string | null]
	actions: [actions: DashboardAction[]]
}>()

// The dashboard on screen. Not the placement, which is the host's reference to it.
const shown = useDashboardView(() => placedDashboard(props), 'desk')

// The actions are the body's own, read off it the way every surface reads them.
const body = ref<InstanceType<typeof DashboardBody>>()

// A dashboard that is loading and one the reader may not see are both nameless,
// so the host keeps calling the page whatever it called it until there is a
// title to give.
watchEffect(() => emit('title', shown.title || null))

// Nothing to refresh and nothing to act on until the dashboard is there, and one
// that is not found offers neither. A fresh array every time, because the host
// runs its own copy of Vue and can track nothing of ours — and the list goes
// over as it was built, an action that leads somewhere already carrying the
// absolute Insights URL this island's router resolves.
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
