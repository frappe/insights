<script setup lang="tsx">
import { useMagicKeys, useStorage, whenever } from '@vueuse/core'
import { Breadcrumbs, TabButtons, call } from 'frappe-ui'
import { ListEmptyState, ListHeader, ListRows, ListView } from 'frappe-ui/experimental'
import { LayoutTemplate as LayoutTemplateIcon, PlusIcon, SearchIcon } from 'lucide-vue-next'
import { computed, ref, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { wheneverChanges } from '../helpers'
import { __ } from '../translation'
import useUserStore from '../users/users'
import useWorkbook, { newWorkbookName } from './workbook'
import { getWorkbookColumns } from './workbookListColumns'
import useWorkbooks from './workbooks'
import WorkbookLibrary, { StandardWorkbook } from './WorkbookLibrary.vue'
import { useTelemetry } from '@framework/ui/telemetry/index.ts'

const router = useRouter()
const userStore = useUserStore()
const workbookStore = useWorkbooks()
const { capture } = useTelemetry()

type WorkbookScope = 'all' | 'owned' | 'shared'

const scopeTabs: { label: string; value: WorkbookScope }[] = [
	{ label: __('All'), value: 'all' },
	{ label: __('Created'), value: 'owned' },
	{ label: __('Shared'), value: 'shared' },
]

// persist the chosen scope locally so it survives reloads
const scope = useStorage<WorkbookScope>('insights:workbook-scope', 'all')
const searchQuery = ref('')

// "Load more" grows the page size and refetches
const PAGE_SIZE = 20
const limit = ref(PAGE_SIZE)
const hasMore = computed(() => workbookStore.workbooks.length >= limit.value)

async function refresh() {
	workbookStore.getWorkbooks(searchQuery.value, limit.value, scope.value)
}

// reset pagination for a new query (scope/search change)
function reload() {
	limit.value = PAGE_SIZE
	refresh()
}

function loadMore() {
	limit.value += PAGE_SIZE
	refresh()
}

// reset the list when the scope changes so a slow fetch can't keep showing the
// previous scope's workbooks; search keeps previous data (no flicker)
wheneverChanges(
	() => scope.value,
	() => {
		workbookStore.workbooks = []
		reload()
	},
	{ immediate: true },
)
wheneverChanges(searchQuery, reload, { debounce: 300 })

// ---- create workbook ----
const creatingWorkbook = ref(false)
function openNewWorkbook() {
	creatingWorkbook.value = true
	useWorkbook(newWorkbookName())
		.insert()
		.then((doc) => router.push(`/workbook/${doc.name}`))
		.finally(() => (creatingWorkbook.value = false))
}

// the dashboards installed apps ship, already on this site — a permanent
// "Library" button surfaces them whenever there are any. The list is filtered
// server-side by what the user's audience admits, so there is no role gate here.
const shippedWorkbooks = ref<StandardWorkbook[]>([])
const showLibrary = ref(false)
call('insights.api.standard_content.get_standard_content').then(
	(data: StandardWorkbook[]) => (shippedWorkbooks.value = data || []),
)

function openLibrary() {
	showLibrary.value = true
	capture('workbook_library_opened')
}

const columns = getWorkbookColumns({ userStore })

function onRowClick(row: any) {
	router.push(`/workbook/${row.name}`)
}

const listOptions = computed(() => ({
	columns,
	rows: workbookStore.workbooks,
	rowKey: 'name',
	options: {
		showTooltip: false,
		onRowClick,
		// actions are rendered via the ListEmptyState slot below — the built-in
		// supports only one button, and we want New + Library side by side
		emptyState: {
			title: __('No Workbooks'),
			description: __('No workbooks to display.'),
		},
	},
}))

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
				v-if="shippedWorkbooks.length"
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

	<WorkbookLibrary v-model="showLibrary" :workbooks="shippedWorkbooks" />

	<div class="mb-4 flex h-full flex-col gap-3 overflow-auto px-5 pt-3">
		<div class="flex items-center justify-between gap-2 overflow-visible py-1">
			<FormControl
				class="w-64"
				:placeholder="__('Search by title')"
				v-model="searchQuery"
				:debounce="300"
				autocomplete="off"
			>
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-ink-gray-4" />
				</template>
			</FormControl>
			<TabButtons :options="scopeTabs" v-model="scope" />
		</div>
		<!-- flex parent so ListView (whose root is flex-1) fills the height, which
		lets the empty state center vertically instead of collapsing to the top -->
		<div class="flex w-full flex-1 flex-col">
			<ListView class="h-full" v-bind="listOptions">
				<ListHeader />
				<ListRows v-if="workbookStore.workbooks.length" />
				<!-- skip the empty state while a fetch is in flight so it doesn't flash on tab switch -->
				<!-- ListEmptyState already centers its slot content -->
				<ListEmptyState v-else-if="!workbookStore.loading">
					<div class="text-2xl-medium text-ink-gray-8">
						{{ __('No Workbooks') }}
					</div>
					<div class="mt-1 text-base text-ink-gray-5">
						{{
							shippedWorkbooks.length
								? __('Create a workbook, or start from a prebuilt one.')
								: __('No workbooks to display.')
						}}
					</div>
					<div class="mt-4 flex items-center gap-2">
						<Button
							v-if="shippedWorkbooks.length"
							:label="__('Library')"
							variant="outline"
							@click="openLibrary"
						>
							<template #prefix>
								<LayoutTemplateIcon class="w-4" />
							</template>
						</Button>
						<Button
							v-if="scope !== 'shared'"
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
				</ListEmptyState>
			</ListView>
			<div v-if="hasMore" class="flex pt-3">
				<Button
					:label="__('Load more')"
					:loading="workbookStore.loading"
					@click="loadMore"
				/>
			</div>
		</div>
	</div>
</template>
