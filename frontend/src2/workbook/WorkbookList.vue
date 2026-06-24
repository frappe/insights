<script setup lang="tsx">
import { useMagicKeys, useStorage, whenever } from '@vueuse/core'
import { Breadcrumbs, ListEmptyState, ListHeader, ListRows, ListView, TabButtons } from 'frappe-ui'
import { PlusIcon, SearchIcon } from 'lucide-vue-next'
import { computed, ref, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { wheneverChanges } from '../helpers'
import { __ } from '../translation'
import useUserStore from '../users/users'
import useWorkbook, { newWorkbookName } from './workbook'
import { getWorkbookColumns } from './workbookListColumns'
import useWorkbooks from './workbooks'

const router = useRouter()
const userStore = useUserStore()
const workbookStore = useWorkbooks()

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
		emptyState: {
			title: __('No Workbooks'),
			description: __('No workbooks to display.'),
			button:
				scope.value !== 'shared'
					? {
							label: __('New Workbook'),
							variant: 'solid',
							onClick: openNewWorkbook,
							loading: creatingWorkbook.value,
					  }
					: undefined,
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
			<FormControl
				class="w-64"
				:placeholder="__('Search by title')"
				v-model="searchQuery"
				:debounce="300"
				autocomplete="off"
			>
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" />
				</template>
			</FormControl>
			<TabButtons :buttons="scopeTabs" v-model="scope" />
		</div>
		<!-- plain block wrapper so ListView flows to content height (its root is
		flex-1 and would otherwise stretch and leave whitespace) -->
		<div class="w-full">
			<ListView v-bind="listOptions">
				<ListHeader />
				<ListRows v-if="workbookStore.workbooks.length" />
				<!-- skip the empty state while a fetch is in flight so it doesn't flash on tab switch -->
				<ListEmptyState v-else-if="!workbookStore.loading" />
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
