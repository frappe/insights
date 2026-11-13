<script setup lang="ts">
import { Filter, serializeFilters, type FilterField } from '@framework/ui/Filter'
import { QuickFilter } from '@framework/ui/QuickFilter'
import { Breadcrumbs, MultiSelect, TabButtons } from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow } from 'frappe-ui/list'
import { LayoutGrid, List as ListIcon, MoreVertical, SearchIcon, Star } from 'lucide-vue-next'
import { computed, ref, toRef, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { AccessSource, useAccessSources } from '../components/access'
import AccessLabel from '../components/AccessLabel.vue'
import OwnerAvatar from '../components/OwnerAvatar.vue'
import { showErrorToast, wheneverChanges } from '../helpers'
import session from '../session'
import { __ } from '../translation'
import DashboardCard from './DashboardCard.vue'
import useDashboardStore, {
	canOpenWorkbook,
	DashboardListItem,
	useDashboardView,
} from './dashboards'

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

// A reader without an Insights role gets every dashboard they may open at
// once, and none of the controls that call the builder's endpoints: filters,
// access sources, favorites and the card menu. They search by title here.
const isReader = !session.isAuthorized

const view = useDashboardView()
const views = [
	{ value: 'grid', icon: LayoutGrid, label: __('Grid') },
	{ value: 'list', icon: ListIcon, label: __('List') },
]
// a reader cannot open the workbook or list who else may open a dashboard
const listColumns = isReader
	? ['minmax(0,1fr)', '8rem', '8rem']
	: ['minmax(0,1fr)', '11rem', '10rem', '8rem', '8rem', '4.5rem']
const titleSearch = ref('')
const listed = computed(() => {
	if (!isReader) return store.dashboards
	const term = titleSearch.value.toLowerCase()
	return store.dashboards.filter((d) => d.title.toLowerCase().includes(term))
})

// "Load more" grows the page size and refetches
const PAGE_SIZE = 20
const limit = ref(PAGE_SIZE)
// favourites always come back whole, so only the rest count against the page
const otherDashboards = computed(() => listed.value.filter((d) => !d.is_favourite))
const hasMore = computed(() => !isReader && otherDashboards.value.length >= limit.value)
const groups = computed(() =>
	[
		{ label: __('Favorites'), dashboards: listed.value.filter((d) => d.is_favourite) },
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

const isNarrowed = computed(() => wireFilters.value.length > 0 || Boolean(titleSearch.value))

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
if (!isReader) wheneverChanges(wireFilters, reload, { debounce: 300 })

const dropdownOptions = (dashboard: DashboardListItem) =>
	isReader ? [] : builderOptions(dashboard)

const builderOptions = (dashboard: DashboardListItem) => [
	{
		label: dashboard.is_favourite ? __('Remove from favorites') : __('Add to favorites'),
		icon: 'lucide-star',
		onClick: () => toggleFavorite(dashboard),
	},
	...(canOpenWorkbook(dashboard)
		? [
				{
					label: __('Open Workbook'),
					icon: 'lucide-external-link',
					onClick: () => router.push(`/workbook/${dashboard.workbook}`),
				},
		  ]
		: []),
	...(dashboard.can_write && dashboard.same_rows_for_every_reader
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
			<FormControl
				v-if="isReader"
				:placeholder="__('Search by Title')"
				v-model="titleSearch"
				:debounce="300"
			>
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-ink-gray-4" />
				</template>
			</FormControl>
			<div v-else class="flex min-w-0 flex-1 items-center gap-2">
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
			<TabButtons v-model="view" :options="views" />
		</div>

		<div class="h-full w-full">
			<List
				v-if="listed.length && view === 'list'"
				class="-mx-3 list-row-px-3"
				:columns="listColumns"
				:row-height="40"
			>
				<ListHeader class="sticky top-0 z-10 bg-surface-base">
					<ListHeaderCell>{{ __('Title') }}</ListHeaderCell>
					<template v-if="!isReader">
						<ListHeaderCell>{{ __('Workbook') }}</ListHeaderCell>
						<ListHeaderCell>{{ __('Access') }}</ListHeaderCell>
					</template>
					<ListHeaderCell>{{ __('Opened') }}</ListHeaderCell>
					<ListHeaderCell>{{ __('Modified') }}</ListHeaderCell>
					<ListHeaderCell v-if="!isReader" />
				</ListHeader>
				<ListRow
					v-for="dashboard in listed"
					:key="dashboard.name"
					class="group/row active:bg-surface-gray-2 sm:rounded-[10px] sm:hover:bg-surface-gray-1"
				>
					<ListCell>
						<RouterLink
							:to="`/dashboards/${dashboard.name}`"
							class="absolute inset-0 sm:rounded-[10px]"
							:aria-label="dashboard.title"
						/>
						<OwnerAvatar
							:owner="dashboard.owner"
							:owner-name="dashboard.owner_name"
							:shipped-by="dashboard.shipped_by"
							:shipped-by-logo="dashboard.shipped_by_logo"
						/>
						<span class="ml-3 truncate text-base text-ink-gray-8">
							{{ dashboard.title }}
						</span>
					</ListCell>
					<template v-if="!isReader">
						<ListCell>
							<span class="truncate text-base text-ink-gray-6">
								{{ dashboard.workbook_title }}
							</span>
						</ListCell>
						<ListCell>
							<AccessLabel :item="dashboard" />
						</ListCell>
					</template>
					<ListCell>
						<span class="truncate text-base text-ink-gray-6">
							{{ dashboard.last_opened_from_now }}
						</span>
					</ListCell>
					<ListCell>
						<span class="truncate text-base text-ink-gray-6">
							{{ dashboard.modified_from_now }}
						</span>
					</ListCell>
					<ListCell v-if="!isReader" class="justify-end">
						<Button
							class="relative"
							:class="
								dashboard.is_favourite
									? ''
									: 'opacity-0 focus-visible:opacity-100 group-hover/row:opacity-100'
							"
							variant="ghost"
							:label="
								dashboard.is_favourite
									? __('Remove from favorites')
									: __('Add to favorites')
							"
							@click="toggleFavorite(dashboard)"
						>
							<template #icon>
								<Star
									class="h-4 w-4"
									:class="
										dashboard.is_favourite
											? 'fill-ink-amber-4 text-ink-amber-4'
											: 'text-ink-gray-5'
									"
								/>
							</template>
						</Button>
						<Dropdown :options="dropdownOptions(dashboard)">
							<Button class="relative" variant="ghost" :label="__('More')">
								<template #icon>
									<MoreVertical
										class="h-4 w-4 text-ink-gray-6"
										stroke-width="1.5"
									/>
								</template>
							</Button>
						</Dropdown>
					</ListCell>
				</ListRow>
			</List>

			<div v-else-if="listed.length" class="flex flex-col gap-12">
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
							@toggle-favorite="toggleFavorite(dashboard)"
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
				v-if="!listed.length && !store.loading"
				class="flex h-full w-full flex-col items-center justify-center text-base"
			>
				<div class="text-2xl-medium">
					{{
						isNarrowed
							? __('No dashboards found')
							: isReader
							  ? __("You don't have access to any dashboards")
							  : __('No dashboards')
					}}
				</div>
				<div class="mt-1 text-base text-ink-gray-5">
					{{
						isNarrowed
							? __('Try a different filter.')
							: isReader
							  ? __('Ask an administrator to share a dashboard with you.')
							  : __('Dashboards you create or are shared with you show up here.')
					}}
				</div>
				<Button
					v-if="isReader && !isNarrowed && session.user.has_desk_access"
					class="mt-3"
					:label="__('Open Desk')"
					href="/desk"
				/>
			</div>
		</div>
	</div>
</template>
