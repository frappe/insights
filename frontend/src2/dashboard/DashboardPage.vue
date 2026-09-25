<script setup lang="ts">
import { Breadcrumbs } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { __ } from '../translation'
import DashboardActions from './DashboardActions.vue'
import DashboardBody from './DashboardBody.vue'
import StaticGridLayout from './StaticGridLayout.vue'
import DashboardItemView from './DashboardItemView.vue'
import type { DashboardView } from './view'

// A dashboard as a whole page: a header with breadcrumbs, and the dashboard
// under it. The public link and the SPA's dashboard page mount it. The builder
// does not, because its workbook already has a navbar. The desk island does not
// either, because desk renders its own page header.
//
// The dashboard itself belongs to `DashboardBody`.
type PageCrumb = { label: string; route: string }

const props = defineProps<{
	dashboard: DashboardView
	// the parents of this page only. This component adds the last crumb
	breadcrumbs?: PageCrumb[]
}>()

// `DashboardBody` decides the actions. This page reads them through the ref and
// renders them in its header.
const body = ref<InstanceType<typeof DashboardBody>>()

// A loading dashboard and a Not Found one get the same title, so the header
// never says whether the dashboard exists.
const pageTitle = computed(() => props.dashboard.title || __('Dashboard'))

const crumbs = computed(() => [...(props.breadcrumbs || []), { label: pageTitle.value }])

watch(pageTitle, (title) => (document.title = `${title} | Insights`), { immediate: true })
</script>

<template>
	<div class="flex h-full w-full flex-col overflow-hidden">
		<!-- The header belongs to this page, not the body, so it renders in every
		     state. A reader who gets Not Found still has a way back. -->
		<div
			class="flex h-12 flex-shrink-0 items-center justify-between gap-2 border-b border-outline-gray-1 px-4"
		>
			<div class="flex min-w-0 items-baseline gap-2">
				<Breadcrumbs :items="crumbs" />
			</div>
			<!-- No actions until the dashboard loads, and none on Not Found. -->
			<div
				v-if="!dashboard.loading && !dashboard.notFound"
				class="flex flex-shrink-0 items-center gap-1"
			>
				<DashboardActions :actions="body?.actions || []" />
			</div>
		</div>

		<DashboardBody
			ref="body"
			class="min-h-0 flex-1"
			:dashboard="dashboard"
			:grid="StaticGridLayout"
			:cell="DashboardItemView"
		/>
	</div>
</template>
