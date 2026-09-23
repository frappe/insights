<script setup lang="ts">
import { Filter, serializeFilters, type FilterField } from '@framework/ui/Filter'
import { QuickFilter } from '@framework/ui/QuickFilter'
import { useMagicKeys, whenever } from '@vueuse/core'
import { Avatar, Breadcrumbs, MultiSelect, call } from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow } from 'frappe-ui/list'
import { LayoutTemplate as LayoutTemplateIcon, PlusIcon } from 'lucide-vue-next'
import { accessIcon, accessLabel, AccessSource, useAccessSources } from '../components/access'
import { computed, ref, toRef, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { wheneverChanges } from '../helpers'
import session from '../session'
import { __ } from '../translation'
import { WorkbookListItem } from '../types/workbook.types'
import useUserStore from '../users/users'
import useWorkbook, { newWorkbookName } from './workbook'
import useWorkbooks from './workbooks'
import WorkbookTemplates, { WorkbookTemplate } from './WorkbookTemplates.vue'
import { useTelemetry } from '../telemetry'

const router = useRouter()
const userStore = useUserStore()
const workbookStore = useWorkbooks()
const { capture } = useTelemetry()

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

// workbook library (the prebuilt workbooks installed apps seed) — a permanent
// "Library" button surfaces it whenever the library is non-empty. importing is an admin
// action for v1, so only admins fetch it; non-admins just receive the shared
// workbooks in their list once an admin imports.
const templates = ref<WorkbookTemplate[]>([])
const showTemplates = ref(false)
function fetchTemplates() {
	if (!session.user.is_admin) return
	call('insights.api.templates.get_workbook_templates').then(
		(data: WorkbookTemplate[]) => (templates.value = data || []),
	)
}
wheneverChanges(() => session.user.is_admin, fetchTemplates, { immediate: true })

function openLibrary() {
	showTemplates.value = true
	capture('workbook_library_opened')
}

const isNarrowed = computed(() => wireFilters.value.length > 0)

const keys = useMagicKeys()
const cmdV = keys['Meta+V']
whenever(cmdV, () => {
	if (!navigator.clipboard) return
	navigator.clipboard.readText().then((text) => {
		try {
			const json = JSON.parse(text)
			if (json.type === 'Workbook') {
				workbookStore.importWorkbook(json)
			}
		} catch (e) {}
	})
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
				v-if="templates.length"
				:label="__('Library')"
				variant="outline"
				@click="openLibrary"
			>
				<template #prefix>
					<LayoutTemplateIcon class="w-4" />
				</template>
			</Button>
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

	<WorkbookTemplates v-model="showTemplates" :templates="templates" @refresh="fetchTemplates" />

	<div class="mb-4 flex h-full flex-col gap-3 overflow-auto px-5 pt-3">
		<div class="flex items-center justify-between gap-2 overflow-visible py-1">
			<div class="flex min-w-0 flex-1 items-center gap-2">
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
		</div>

		<List
			v-if="workbookStore.workbooks.length"
			class="-mx-3 list-row-px-3"
			:columns="['minmax(0,1fr)', '11rem', '10rem', '8rem', '8rem']"
			:row-height="40"
		>
			<ListHeader class="sticky top-0 z-10 bg-surface-base">
				<ListHeaderCell>{{ __('Title') }}</ListHeaderCell>
				<ListHeaderCell>{{ __('Data Source') }}</ListHeaderCell>
				<ListHeaderCell>{{ __('Access') }}</ListHeaderCell>
				<ListHeaderCell>{{ __('Opened') }}</ListHeaderCell>
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
					<Tooltip :text="userStore.getName(workbook.owner) || workbook.owner">
						<Avatar
							class="relative shrink-0"
							size="sm"
							:label="userStore.getName(workbook.owner) || workbook.owner"
							:image="userStore.getImage(workbook.owner)"
						/>
					</Tooltip>
					<span class="ml-3 truncate text-base text-ink-gray-8">{{
						workbook.title
					}}</span>
				</ListCell>
				<ListCell>
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
				<ListCell>
					<component :is="accessIcon(workbook)" class="size-4 shrink-0 text-ink-gray-5" />
					<span class="ml-2 truncate text-base text-ink-gray-6">
						{{ accessLabel(workbook, userStore.getName) }}
					</span>
				</ListCell>
				<ListCell>
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
						: templates.length
						  ? __('Create a workbook, or start from a prebuilt one.')
						  : __('No workbooks to display.')
				}}
			</div>
			<div v-if="!isNarrowed" class="mt-4 flex items-center gap-2">
				<Button
					v-if="templates.length"
					:label="__('Library')"
					variant="outline"
					@click="openLibrary"
				>
					<template #prefix>
						<LayoutTemplateIcon class="w-4" />
					</template>
				</Button>
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
