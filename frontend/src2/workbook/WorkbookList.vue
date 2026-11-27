<script setup lang="ts">
import { Filter, serializeFilters, type FilterField } from '@framework/ui/Filter'
import { applyQuick, QuickFilter, quickOperator, quickValue } from '@framework/ui/QuickFilter'
import { useMagicKeys, whenever } from '@vueuse/core'
import { BottomSheet, Breadcrumbs, MultiSelect } from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow } from 'frappe-ui/list'
import { ListFilter, PlusIcon, SearchIcon } from 'lucide-vue-next'
import { access, AccessSource, useAccessSources } from '../components/access'
import AccessLabel from '../components/AccessLabel.vue'
import OwnerAvatar from '../components/OwnerAvatar.vue'
import { computed, ref, toRef, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { wheneverChanges } from '../helpers'
import { __ } from '../translation'
import useUserStore from '../users/users'
import { WorkbookListItem } from '../types/workbook.types'
import useWorkbook, { newWorkbookName } from './workbook'
import { pastedWorkbook } from './workbook_file'
import useWorkbooks from './workbooks'

const router = useRouter()
const workbookStore = useWorkbooks()
const userStore = useUserStore()

const {
	options: sourceOptions,
	selected: selectedSources,
	shown: shownSources,
	sources,
} = useAccessSources('insights:workbook-access')

const filters = toRef(workbookStore, 'filters')
const wireFilters = computed(() => serializeFilters(filters.value))
// resolved by `get_workbooks`: a record field matches the picked document, and
// data source and table match inside each query's JSON. `name` is the Title
// field, so the quick filter types a title and flips to a workbook pick.
const field = (fieldname: string, label: string, fieldtype: string, options?: string) =>
	({ fieldname, value: fieldname, label, fieldtype, options }) as FilterField
const titleField = field('name', __('Title'), 'Link', 'Insights Workbook')
const queryField = field('query', __('Query'), 'Link', 'Insights Query v3')
const dataSourceField = field('data_source', __('Data Source'), 'Link', 'Insights Data Source v3')
const tableField = field('table_name', __('Table'), 'Link', 'Insights Table v3')
const quickFields = [titleField, dataSourceField, tableField, queryField]
const filterFields = [
	titleField,
	queryField,
	field('chart', __('Chart'), 'Link', 'Insights Chart v3'),
	field('dashboard', __('Dashboard'), 'Link', 'Insights Dashboard v3'),
	dataSourceField,
	tableField,
	'owner',
	'modified',
]

// On a phone the title quick filter is a search box across the width, and the
// rest of the filters wait in a sheet behind one button
const phoneTitle = computed({
	get: () => String(quickValue(filters.value, titleField)),
	set: (value: string) =>
		(filters.value = applyQuick(
			filters.value,
			titleField,
			value,
			quickOperator(filters.value, titleField),
		)),
})
const showFilterSheet = ref(false)
const sheetFilterCount = computed(
	() => filters.value.filter((f) => f.fieldname !== titleField.fieldname).length,
)

// the one line under a phone row's title
function phoneMeta(workbook: WorkbookListItem) {
	const sources =
		workbook.data_sources.length > 1
			? `${workbook.data_sources[0]} +${workbook.data_sources.length - 1}`
			: workbook.data_sources[0]
	return [sources, access(workbook, userStore.getName).label, workbook.modified_from_now]
		.filter(Boolean)
		.join(' · ')
}

// "Load more" grows the page size and refetches
const PAGE_SIZE = 20
const limit = ref(PAGE_SIZE)
const hasMore = computed(() => workbookStore.workbooks.length >= limit.value)

async function refresh() {
	workbookStore.getWorkbooks(undefined, limit.value, sources.value, wireFilters.value)
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

// reset the list when the sources change so a slow fetch can't keep showing the
// previous sources' workbooks; search keeps previous data (no flicker)
wheneverChanges(
	() => sources.value,
	() => {
		workbookStore.workbooks = []
		reload()
	},
	{ immediate: true },
)
wheneverChanges(wireFilters, reload, { debounce: 300 })

// ---- create workbook ----
const creatingWorkbook = ref(false)
function openNewWorkbook() {
	creatingWorkbook.value = true
	useWorkbook(newWorkbookName())
		.insert()
		.then((doc) => router.push(`/workbook/${doc.name}`))
		.finally(() => (creatingWorkbook.value = false))
}

const isNarrowed = computed(() => wireFilters.value.length > 0)

const keys = useMagicKeys()
const cmdV = keys['Meta+V']
whenever(cmdV, () => {
	if (!navigator.clipboard) return
	navigator.clipboard
		.readText()
		.then(pastedWorkbook)
		.then((workbook) => workbook && workbookStore.importWorkbook(workbook))
})

watchEffect(() => {
	document.title = 'Workbooks | Insights'
})
</script>

<template>
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs :items="[{ label: __('Workbooks'), route: '/workbook' }]" />
		<div class="flex items-center gap-2">
			<Button
				:label="__('New Workbook')"
				variant="solid"
				@click="openNewWorkbook"
				:loading="creatingWorkbook"
			>
				<template #prefix>
					<PlusIcon class="w-4" />
				</template>
			</Button>
		</div>
	</header>

	<div class="mb-4 flex h-full flex-col gap-3 overflow-auto px-5 pt-3">
		<div class="flex items-center justify-between gap-2 overflow-visible py-1">
			<div class="flex min-w-0 flex-1 items-center gap-2 max-sm:hidden">
				<QuickFilter
					class="min-w-0"
					doctype="Insights Workbook"
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
					doctype="Insights Workbook"
					align="start"
					:fields="filterFields"
					v-model="filters"
				/>
			</div>
			<FormControl
				class="flex-1 sm:hidden"
				:placeholder="__('Search by Title')"
				v-model="phoneTitle"
				:debounce="300"
			>
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-ink-gray-4" />
				</template>
			</FormControl>
			<Button
				class="sm:hidden"
				size="md"
				:aria-label="__('Filters')"
				@click="showFilterSheet = true"
			>
				<template v-if="sheetFilterCount" #prefix>
					<ListFilter class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
				</template>
				<template v-else #icon>
					<ListFilter class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
				</template>
				<template v-if="sheetFilterCount">{{ sheetFilterCount }}</template>
			</Button>
		</div>

		<BottomSheet v-model:open="showFilterSheet" :title="__('Filters')">
			<div class="flex flex-col gap-4 px-4 pb-6">
				<MultiSelect
					class="w-full"
					variant="subtle"
					:placeholder="__('Access')"
					:options="sourceOptions"
					:modelValue="shownSources"
					@update:modelValue="(next) => (selectedSources = next as AccessSource[])"
				/>
				<QuickFilter
					doctype="Insights Workbook"
					:fields="[dataSourceField, tableField, queryField]"
					v-model:filters="filters"
				/>
				<Filter
					doctype="Insights Workbook"
					align="start"
					:fields="filterFields"
					v-model="filters"
				/>
			</div>
		</BottomSheet>

		<!-- a phone has one view: two-line rows, the title across the width -->
		<List
			v-if="workbookStore.workbooks.length"
			class="-mx-3 list-row-px-3 sm:hidden"
			:columns="['2rem', 'minmax(0,1fr)']"
			:row-height="56"
		>
			<ListRow
				v-for="workbook in workbookStore.workbooks"
				:key="workbook.name"
				class="active:bg-surface-gray-2"
			>
				<ListCell>
					<RouterLink
						:to="`/workbook/${workbook.name}`"
						class="absolute inset-0"
						:aria-label="workbook.title"
					/>
					<OwnerAvatar
						:owner="workbook.owner"
						:shipped-by="workbook.shipped_by"
						:shipped-by-logo="workbook.shipped_by_logo"
					/>
				</ListCell>
				<ListCell class="flex-col !items-start justify-center">
					<span class="w-full truncate text-base text-ink-gray-8">
						{{ workbook.title }}
					</span>
					<span class="w-full truncate text-sm text-ink-gray-5">
						{{ phoneMeta(workbook) }}
					</span>
				</ListCell>
			</ListRow>
		</List>

		<List
			v-if="workbookStore.workbooks.length"
			class="-mx-3 list-row-px-3 max-sm:hidden"
			:columns="{
				base: ['minmax(0,1fr)', '6rem'],
				lg: ['minmax(0,1fr)', '11rem', '10rem', '8rem', '8rem'],
			}"
			:row-height="40"
		>
			<ListHeader class="sticky top-0 z-10 bg-surface-base">
				<ListHeaderCell>{{ __('Title') }}</ListHeaderCell>
				<ListHeaderCell class="max-lg:hidden">{{ __('Data Source') }}</ListHeaderCell>
				<ListHeaderCell class="max-lg:hidden">{{ __('Access') }}</ListHeaderCell>
				<ListHeaderCell class="max-lg:hidden">{{ __('Opened') }}</ListHeaderCell>
				<ListHeaderCell>{{ __('Modified') }}</ListHeaderCell>
			</ListHeader>
			<ListRow
				v-for="workbook in workbookStore.workbooks"
				:key="workbook.name"
				class="active:bg-surface-gray-2 sm:rounded-[10px] sm:hover:bg-surface-gray-1"
			>
				<ListCell>
					<RouterLink
						:to="`/workbook/${workbook.name}`"
						class="absolute inset-0 sm:rounded-[10px]"
						:aria-label="workbook.title"
					/>
					<OwnerAvatar
						:owner="workbook.owner"
						:shipped-by="workbook.shipped_by"
						:shipped-by-logo="workbook.shipped_by_logo"
					/>
					<span class="ml-3 truncate text-base text-ink-gray-8">{{
						workbook.title
					}}</span>
				</ListCell>
				<ListCell class="max-lg:hidden">
					<span class="truncate text-base text-ink-gray-6">
						{{ workbook.data_sources[0] }}
					</span>
					<span
						v-if="workbook.data_sources.length > 1"
						class="ml-1 shrink-0 text-base text-ink-gray-5"
					>
						+{{ workbook.data_sources.length - 1 }}
					</span>
				</ListCell>
				<ListCell class="max-lg:hidden">
					<AccessLabel :item="workbook" />
				</ListCell>
				<ListCell class="max-lg:hidden">
					<span class="truncate text-base text-ink-gray-6">
						{{ workbook.last_opened_from_now }}
					</span>
				</ListCell>
				<ListCell>
					<span class="truncate text-base text-ink-gray-6">
						{{ workbook.modified_from_now }}
					</span>
				</ListCell>
			</ListRow>
		</List>

		<!-- skip the empty state while a fetch is in flight so it doesn't flash on tab switch -->
		<div
			v-else-if="!workbookStore.loading"
			class="flex flex-1 flex-col items-center justify-center text-center"
		>
			<div class="text-2xl-medium text-ink-gray-8">
				{{ isNarrowed ? __('No workbooks found') : __('No Workbooks') }}
			</div>
			<div class="mt-1 text-base text-ink-gray-5">
				{{
					isNarrowed
						? __('Try a different search or filter.')
						: __('No workbooks to display.')
				}}
			</div>
			<div v-if="!isNarrowed" class="mt-4 flex items-center gap-2">
				<Button
					v-if="sources.includes('created')"
					:label="__('New Workbook')"
					variant="solid"
					:loading="creatingWorkbook"
					@click="openNewWorkbook"
				>
					<template #prefix>
						<PlusIcon class="w-4" />
					</template>
				</Button>
			</div>
		</div>

		<div v-if="hasMore" class="flex pb-3">
			<Button :label="__('Load more')" :loading="workbookStore.loading" @click="loadMore" />
		</div>
	</div>
</template>
