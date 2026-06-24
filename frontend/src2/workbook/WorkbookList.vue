<script setup lang="tsx">
import { useMagicKeys, useStorage, whenever } from '@vueuse/core'
import {
	Breadcrumbs,
	Dropdown,
	ListEmptyState,
	ListHeader,
	ListRows,
	ListSelectBanner,
	ListView,
	TabButtons,
} from 'frappe-ui'
import { ChevronDown, Folder, FolderPlus, PlusIcon, SearchIcon } from 'lucide-vue-next'
import { computed, ref, toRef, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { wheneverChanges } from '../helpers'
import session from '../session'
import { __ } from '../translation'
import { WorkbookListItem } from '../types/workbook.types'
import useUserStore from '../users/users'
import { useFolderActions } from './useFolderActions'
import { useFolderNavigation } from './useFolderNavigation'
import useWorkbook, { newWorkbookName } from './workbook'
import useWorkbookFolders, { buildFolderMoveOptions } from './workbookFolders'
import { getWorkbookColumns } from './workbookListColumns'
import useWorkbooks from './workbooks'

const router = useRouter()
const userStore = useUserStore()
const workbookStore = useWorkbooks()
const folderStore = useWorkbookFolders()
const isAdmin = computed(() => session.user.is_admin)

const folders = toRef(folderStore, 'folders')
const { currentFolder, searchQuery, drillInto, subfolders, breadcrumbs } = useFolderNavigation(
	folders,
	__('Workbooks'),
)

type WorkbookScope = 'all' | 'owned' | 'shared'

const scopeTabs: { label: string; value: WorkbookScope }[] = [
	{ label: __('All'), value: 'all' },
	{ label: __('Created'), value: 'owned' },
	{ label: __('Shared'), value: 'shared' },
]

// persist the chosen scope locally so it survives reloads
const scope = useStorage<WorkbookScope>('insights:workbook-scope', 'all')

// "Load more" grows the page size and refetches
const PAGE_SIZE = 20
const limit = ref(PAGE_SIZE)
const hasMore = computed(() => workbookStore.workbooks.length >= limit.value)

async function refresh() {
	workbookStore.getWorkbooks(
		searchQuery.value,
		limit.value,
		scope.value,
		currentFolder.value || 'root',
	)
}

// reset pagination for a new query (scope/folder/search change)
function reload() {
	limit.value = PAGE_SIZE
	refresh()
}

function loadMore() {
	limit.value += PAGE_SIZE
	refresh()
}

// reset the list when the folder/scope changes so a slow fetch can't keep
// showing the previous folder's workbooks; search keeps previous data (no flicker)
wheneverChanges(
	() => [scope.value, currentFolder.value],
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

// ---- folder actions ----
const { openNewFolder, renameFolder, deleteFolder } = useFolderActions(
	folderStore,
	refresh,
	currentFolder,
)
const newButtonOptions = computed(() => [
	{ label: __('New Folder'), icon: FolderPlus, onClick: openNewFolder },
])

async function moveWorkbook(workbook: string, folder: string | null) {
	await folderStore.moveWorkbookToFolder(workbook, folder)
	refresh()
}

// ---- bulk move (ListView selection); keys look like "workbook:5" / "folder:3" ----
function bulkMoveOptions(selections: Set<string>, unselectAll: () => void) {
	return buildFolderMoveOptions(folders.value, currentFolder.value, async (folder) => {
		const names = [...selections]
			.filter((key) => key.startsWith('workbook:'))
			.map((key) => key.slice('workbook:'.length))
		if (!names.length) return
		await folderStore.moveWorkbooksToFolder(names, folder)
		unselectAll()
		refresh()
	})
}

const columns = getWorkbookColumns({
	userStore,
	isAdmin,
	folders,
	onRenameFolder: renameFolder,
	onDeleteFolder: deleteFolder,
	onMoveWorkbook: moveWorkbook,
})

function onRowClick(row: any) {
	if (row.__type === 'folder') {
		drillInto(row.name)
	} else {
		router.push(`/workbook/${row.name}`)
	}
}

const rows = computed(() => [
	...subfolders.value.map((f) => ({ ...f, __type: 'folder', _key: `folder:${f.name}` })),
	...workbookStore.workbooks.map((w: WorkbookListItem) => ({
		...w,
		__type: 'workbook',
		_key: `workbook:${w.name}`,
	})),
])

const listOptions = computed(() => ({
	columns,
	rows: rows.value,
	rowKey: '_key',
	options: {
		showTooltip: false,
		onRowClick,
		emptyState: {
			title: currentFolder.value ? __('Empty Folder') : __('No Workbooks'),
			description: currentFolder.value
				? __('No folders or workbooks here.')
				: __('No workbooks to display.'),
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
		<Breadcrumbs :items="breadcrumbs" />
		<div class="flex items-center gap-2">
			<div class="flex items-center">
				<Button
					:label="__('New Workbook')"
					variant="solid"
					@click="openNewWorkbook"
					:loading="creatingWorkbook"
					:class="isAdmin ? 'rounded-r-none' : ''"
				>
					<template #prefix>
						<PlusIcon class="w-4" />
					</template>
				</Button>
				<Dropdown v-if="isAdmin" :options="newButtonOptions" placement="right">
					<Button variant="solid" class="ml-px rounded-l-none px-1.5">
						<ChevronDown class="w-4" />
					</Button>
				</Dropdown>
			</div>
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
				<ListRows v-if="rows.length" />
				<!-- skip the empty state while a fetch is in flight so it doesn't flash on tab switch -->
				<ListEmptyState v-else-if="!workbookStore.loading" />
				<ListSelectBanner>
					<template #actions="{ selections, unselectAll }">
						<Dropdown
							:options="bulkMoveOptions(selections, unselectAll)"
							placement="right"
						>
							<Button :label="__('Move to folder')" variant="ghost">
								<template #prefix>
									<Folder class="h-4 w-4 text-gray-600" />
								</template>
							</Button>
						</Dropdown>
					</template>
				</ListSelectBanner>
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
