<script setup lang="ts">
import { Filter, serializeFilters, type FilterField } from '@framework/ui/Filter'
import { QuickFilter } from '@framework/ui/QuickFilter'
import { Breadcrumbs, MultiSelect } from 'frappe-ui'
import { computed, ref, toRef, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { AccessSource, useAccessSources } from '../components/access'
import { showErrorToast, wheneverChanges } from '../helpers'
import { __ } from '../translation'
import DashboardCard from './DashboardCard.vue'
import useDashboardStore, { DashboardListItem } from './dashboards'

const store = useDashboardStore()
const router = useRouter()

const {
	options: sourceOptions,
	selected: selectedSources,
	shown: shownSources,
	sources,
} = useAccessSources('insights:dashboard-access')

const filters = toRef(store, 'filters')
const wireFilters = computed(() => serializeFilters(filters.value))
// resolved by `get_dashboards`: a record field matches the picked document.
// `name` is the Title field, so the quick filter types a title and flips to a
// dashboard pick.
const field = (fieldname: string, label: string, fieldtype: string, options?: string) =>
	({ fieldname, value: fieldname, label, fieldtype, options }) as FilterField
const titleField = field('name', __('Title'), 'Link', 'Insights Dashboard v3')
const workbookField = field('workbook', __('Workbook'), 'Link', 'Insights Workbook')
const quickFields = [titleField, workbookField]
const filterFields = [
	titleField,
	workbookField,
	field('chart', __('Chart'), 'Link', 'Insights Chart v3'),
	field('data_source', __('Data Source'), 'Link', 'Insights Data Source v3'),
	'owner',
	'modified',
]

// "Load more" grows the page size and refetches
const PAGE_SIZE = 20
const limit = ref(PAGE_SIZE)
// favourites always come back whole, so only the rest count against the page
const otherDashboards = computed(() => store.dashboards.filter((d) => !d.is_favourite))
const hasMore = computed(() => otherDashboards.value.length >= limit.value)
const groups = computed(() =>
	[
		{ label: __('Favorites'), dashboards: store.dashboards.filter((d) => d.is_favourite) },
		{ label: __('Recent'), dashboards: otherDashboards.value },
	].filter((group) => group.dashboards.length),
)

function refresh() {
	store.fetchDashboards(limit.value, sources.value, wireFilters.value)
}

// reset pagination for a new query (source or filter change)
function reload() {
	limit.value = PAGE_SIZE
	refresh()
}

function loadMore() {
	limit.value += PAGE_SIZE
	refresh()
}

const isNarrowed = computed(() => wireFilters.value.length > 0)

// reset on a source change so a slow fetch can't keep showing the previous
// sources' dashboards; a filter change keeps previous data (no flicker)
wheneverChanges(
	() => sources.value,
	() => {
		store.dashboards = []
		reload()
	},
	{ immediate: true },
)
wheneverChanges(wireFilters, reload, { debounce: 300 })

const dropdownOptions = (dashboard: DashboardListItem) => [
	{
		label: dashboard.is_favourite ? __('Remove from favorites') : __('Add to favorites'),
		icon: 'lucide-star',
		onClick: () => toggleFavorite(dashboard),
	},
	{
		label: __('Open Workbook'),
		icon: 'lucide-external-link',
		onClick: () => router.push(`/workbook/${dashboard.workbook}`),
	},
	...(dashboard.can_write
		? [
				{
					label: __('Refresh Preview'),
					icon: 'lucide-refresh-cw',
					loading: store.updatingPreviewImage,
					onClick: () => store.updatePreviewImage(dashboard.name),
				},
		  ]
		: []),
]

const toggleFavorite = (dashboard: DashboardListItem) => {
	// flip the star at once; the refetch then moves the card between sections
	const next = !dashboard.is_favourite
	dashboard.is_favourite = next
	store
		.toggleLike(dashboard.name, next)
		.then(refresh)
		.catch((error: Error) => {
			dashboard.is_favourite = !next // revert on failure
			showErrorToast(error, false)
		})
}

watchEffect(() => {
	document.title = 'Dashboards | Insights'
})
</script>

<template>
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs :items="[{ label: __('Dashboards'), route: '/dashboards' }]" />
	</header>

	<div class="mb-4 flex h-full flex-col gap-3 overflow-auto px-5 py-3">
		<div class="flex items-center justify-between gap-2 overflow-visible py-1">
			<div class="flex min-w-0 flex-1 items-center gap-2">
				<QuickFilter
					class="min-w-0"
					doctype="Insights Dashboard v3"
					:fields="quickFields"
					v-model:filters="filters"
				/>
				<MultiSelect
					class="w-40 shrink-0"
					variant="subtle"
					:placeholder="__('Access')"
					:options="sourceOptions"
					:modelValue="shownSources"
					@update:modelValue="(next) => (selectedSources = next as AccessSource[])"
				/>
				<Filter
					doctype="Insights Dashboard v3"
					align="start"
					:fields="filterFields"
					v-model="filters"
				/>
			</div>
		</div>

		<div class="h-full w-full">
			<div v-if="store.dashboards.length" class="flex flex-col gap-12">
				<section v-for="group in groups" :key="group.label" class="flex flex-col gap-4">
					<div v-if="groups.length > 1" class="text-base-medium text-ink-gray-6">
						{{ group.label }}
					</div>
					<div
						class="grid grid-cols-1 gap-10 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
					>
						<DashboardCard
							v-for="dashboard in group.dashboards"
							:key="dashboard.name"
							:dashboard="dashboard"
							:dropdown-options="dropdownOptions(dashboard)"
							:preview-loading="store.updatingPreviewImage[dashboard.name]"
							@toggle-favorite="toggleFavorite(dashboard)"
							@update-preview="store.updatePreviewImage(dashboard.name)"
						/>
					</div>
				</section>
			</div>

			<!-- load more -->
			<div v-if="hasMore" class="flex pt-8">
				<Button :label="__('Load more')" :loading="store.loading" @click="loadMore" />
			</div>

			<!-- empty (hidden while a fetch is in flight so it doesn't flash on tab switch) -->
			<div
				v-if="!store.dashboards.length && !store.loading"
				class="flex h-full w-full flex-col items-center justify-center text-base"
			>
				<div class="text-2xl-medium">
					{{ isNarrowed ? __('No dashboards found') : __('No dashboards') }}
				</div>
				<div class="mt-1 text-base text-ink-gray-5">
					{{
						isNarrowed
							? __('Try a different filter.')
							: __('Dashboards you create or are shared with you show up here.')
					}}
				</div>
			</div>
		</div>
	</div>
</template>
