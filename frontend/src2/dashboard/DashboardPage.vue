<script setup lang="ts">
import { Breadcrumbs, PageHeaderBackButton, PageHeaderMobile } from 'frappe-ui'
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
	// lay out at the content's height instead of scrolling inside the window, for a capture
	fullHeight?: boolean
}>()

// `DashboardBody` decides the actions. This page reads them through the ref and
// renders them in its header.
const body = ref<InstanceType<typeof DashboardBody>>()

// A loading, Not Found or No Access dashboard gets the same title, so the header
// says nothing about the dashboard.
const pageTitle = computed(() => props.dashboard.title || __('Dashboard'))

const crumbs = computed(() => [...(props.breadcrumbs || []), { label: pageTitle.value }])
// A phone shows back and the title instead of the trail. A page with no parents,
// such as the public link, has nowhere to go back to.
const parent = computed(() => props.breadcrumbs?.at(-1))
const showsActions = computed(
	() => !props.dashboard.loading && !props.dashboard.notFound && !props.dashboard.noAccess,
)

watch(pageTitle, (title) => (document.title = `${title} | Insights`), { immediate: true })
</script>

<template>
	<div class="flex w-full flex-col" :class="fullHeight ? '' : 'h-full overflow-hidden'">
		<!-- The header belongs to this page, not the body, so it renders in every
		     state. A reader who gets Not Found still has a way back. -->
		<div
			class="flex h-12 flex-shrink-0 items-center justify-between gap-2 border-b border-outline-gray-1 px-4 max-sm:hidden"
		>
			<div class="flex min-w-0 items-baseline gap-2">
				<Breadcrumbs :items="crumbs" />
			</div>
			<!-- No actions until the dashboard loads, and none on Not Found or No Access. -->
			<div v-if="showsActions" class="flex flex-shrink-0 items-center gap-1">
				<DashboardActions :actions="body?.actions || []" />
			</div>
		</div>
		<PageHeaderMobile class="flex-shrink-0 sm:hidden" :title="pageTitle">
			<template v-if="parent" #prefix>
				<PageHeaderBackButton :label="__('Back')" :fallback-route="parent.route" />
			</template>
			<template v-if="showsActions" #suffix>
				<div class="flex items-center gap-1">
					<DashboardActions :actions="body?.actions || []" />
				</div>
			</template>
		</PageHeaderMobile>

		<DashboardBody
			ref="body"
			class="min-h-0 flex-1"
			:dashboard="dashboard"
			:grid="StaticGridLayout"
			:cell="DashboardItemView"
			:full-height="fullHeight"
		/>
	</div>
</template>
