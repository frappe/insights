<script setup lang="ts">
import { Breadcrumbs } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { __ } from '../translation'
import DashboardActions from './DashboardActions.vue'
import DashboardBody from './DashboardBody.vue'
import StaticGridLayout from './StaticGridLayout.vue'
import DashboardItemView from './DashboardItemView.vue'
import type { DashboardView } from './view'

// A dashboard as a page of its own: a header band with the trail through it, and
// the dashboard under it. This is what a surface mounts when the dashboard is
// the whole page — the public link and the SPA's dashboard page. The builder is
// one surface that does not, because the workbook it sits in already has a
// navbar, and the desk island is another: desk draws its own page head.
//
// It carries nothing but the dashboard it draws and the navigation context of
// where it sits. Everything a dashboard actually is belongs to `DashboardBody`.
type PageCrumb = { label: string; route: string }

const props = defineProps<{
	dashboard: DashboardView
	// ancestors of this page, never the page itself — the last crumb is ours
	breadcrumbs?: PageCrumb[]
}>()

// What a reader may do with the dashboard is the dashboard's own answer, so this
// page reads the list where it is drawn and lays it out in its header.
const body = ref<InstanceType<typeof DashboardBody>>()

// A dashboard that is loading and one the reader may not see answer the same
// name, so the header never says whether the content exists.
const pageTitle = computed(() => props.dashboard.title || __('Dashboard'))

const crumbs = computed(() => [...(props.breadcrumbs || []), { label: pageTitle.value }])

watch(pageTitle, (title) => (document.title = `${title} | Insights`), { immediate: true })
</script>

<template>
	<div class="flex h-full w-full flex-col overflow-hidden">
		<!-- The header is this page's, not the body's, so it is drawn in every
		     state the body can be in — a reader who may not see this dashboard
		     still gets a way back. -->
		<div
			class="flex h-12 flex-shrink-0 items-center justify-between gap-2 border-b border-outline-gray-1 px-4"
		>
			<div class="flex min-w-0 items-baseline gap-2">
				<Breadcrumbs :items="crumbs" />
			</div>
			<!-- Nothing to refresh and nothing to act on until the dashboard is
			     there, and a Not Found page offers neither. -->
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
