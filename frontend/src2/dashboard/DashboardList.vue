<script setup lang="tsx">
import { Breadcrumbs } from 'frappe-ui'
import {
	Check,
	Folder,
	FolderOpen,
	GripVertical,
	Pencil,
	Plus,
	SearchIcon,
	Star,
	Trash2,
	X,
} from 'lucide-vue-next'
import { computed, nextTick, ref, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { confirmDialog } from '../helpers/confirm_dialog'
import { __ } from '../translation'
import DashboardCard from './DashboardCard.vue'
import useDashboardStore, { DashboardFolder, DashboardListItem } from './dashboards'

const store = useDashboardStore()
const MAX_FOLDER_TITLE_LENGTH = 50
const searchQuery = ref('')
watchEffect(() => {
	store.fetchDashboards(searchQuery.value)
})

const selectedFolder = ref('')
watchEffect(() => {
	if (!store.loading && !selectedFolder.value) {
		selectedFolder.value = store.favorites.length ? 'favorites' : 'all'
	}
})

const filteredDashboards = computed(() => {
	if (selectedFolder.value === 'favorites') return store.favorites
	if (selectedFolder.value === 'all') return store.dashboards
	return store.dashboards.filter((dashboard) => dashboard.folder === selectedFolder.value)
})

const selectedTitle = computed(() => {
	if (selectedFolder.value === 'favorites') return __('Favorites')
	if (selectedFolder.value === 'all') return __('All Dashboards')
	return (
		store.folders.find((folder) => folder.name === selectedFolder.value)?.title ||
		__('Dashboards')
	)
})

const getFolderTitle = (dashboard: DashboardListItem) => {
	if (selectedFolder.value !== 'all' || !dashboard.folder) return
	return store.folders.find((folder) => folder.name === dashboard.folder)?.title
}

const router = useRouter()
const dropdownOptions = (dashboard: DashboardListItem) => {
	const moveSubmenu = [
		...(dashboard.folder
			? [
					{
						label: __('Remove from folder'),
						icon: 'folder-minus',
						onClick: () => store.moveDashboard(dashboard.name),
					},
			  ]
			: []),
		...store.folders
			.filter((folder) => folder.name !== dashboard.folder)
			.map((folder) => ({
				label: folder.title,
				icon: 'folder',
				onClick: () => store.moveDashboard(dashboard.name, folder.name),
			})),
	]
	return [
		{
			label: __('Open Workbook'),
			icon: 'external-link',
			onClick: () => router.push(`/workbook/${dashboard.workbook}`),
		},
		{
			label: __('Refresh Preview'),
			icon: 'refresh-cw',
			loading: store.updatingPreviewImage,
			onClick: () => store.updatePreviewImage(dashboard.name),
		},
		...(moveSubmenu.length
			? [
					{
						label: __('Move to'),
						icon: 'folder',
						submenu: moveSubmenu,
					},
			  ]
			: []),
	]
}

const toggleFavorite = (dashboard: DashboardListItem) => {
	store.toggleLike(dashboard.name, !dashboard.is_favourite)
}

const creatingFolder = ref(false)
const folderTitle = ref('')
const folderInput = ref<HTMLInputElement>()
async function startCreatingFolder() {
	creatingFolder.value = true
	folderTitle.value = ''
	await nextTick()
	folderInput.value?.focus()
}

async function createFolder() {
	const title = folderTitle.value.trim()
	if (!title) return
	await store.createFolder(title)
	creatingFolder.value = false
}

const editingFolder = ref<string>()
async function startRenaming(folder: DashboardFolder) {
	editingFolder.value = folder.name
	folderTitle.value = folder.title
	await nextTick()
	document.querySelector<HTMLInputElement>(`[data-folder-input="${folder.name}"]`)?.select()
}

async function renameFolder(folder: DashboardFolder) {
	const title = folderTitle.value.trim()
	if (title && title !== folder.title) await store.renameFolder(folder.name, title)
	editingFolder.value = undefined
}

function deleteFolder(folder: DashboardFolder) {
	confirmDialog({
		title: __('Delete Folder'),
		message: __('Dashboards in this folder will remain in All Dashboards. Continue?'),
		theme: 'red',
		onSuccess: async () => {
			await store.deleteFolder(folder.name)
			if (selectedFolder.value === folder.name) selectedFolder.value = 'all'
		},
	})
}

const draggedDashboard = ref<string>()
const draggedFolder = ref<string>()
const dragOverFolder = ref<string>()

function startDashboardDrag(event: DragEvent, dashboard: DashboardListItem) {
	draggedDashboard.value = dashboard.name
	event.dataTransfer?.setData('text/plain', dashboard.name)
	if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
}

function startFolderDrag(event: DragEvent, folder: DashboardFolder) {
	draggedFolder.value = folder.name
	event.dataTransfer?.setData('text/plain', folder.name)
	if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
}

function allowFolderDrop(event: DragEvent, folderName: string) {
	event.preventDefault()
	dragOverFolder.value = folderName
}

async function dropOnFolder(folderName?: string) {
	if (draggedDashboard.value) {
		await store.moveDashboard(draggedDashboard.value, folderName)
	}
	draggedDashboard.value = undefined
	dragOverFolder.value = undefined
}

async function dropFolderBefore(targetFolder: DashboardFolder) {
	if (!draggedFolder.value || draggedFolder.value === targetFolder.name) return
	const folderNames = store.folders.map((folder) => folder.name)
	const from = folderNames.indexOf(draggedFolder.value)
	const to = folderNames.indexOf(targetFolder.name)
	folderNames.splice(to, 0, folderNames.splice(from, 1)[0])
	await store.updateFolderOrder(folderNames)
	draggedFolder.value = undefined
	dragOverFolder.value = undefined
}

function finishDrag() {
	draggedDashboard.value = undefined
	draggedFolder.value = undefined
	dragOverFolder.value = undefined
}

watchEffect(() => {
	document.title = 'Dashboards | Insights'
})
</script>

<template>
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs :items="[{ label: 'Dashboards', route: '/dashboards' }]" />
	</header>

	<div class="flex min-h-0 flex-1">
		<aside class="flex w-56 shrink-0 flex-col border-r bg-gray-50/60 p-3">
			<div class="mb-2 flex items-center justify-between px-2">
				<span class="text-xs font-medium uppercase text-gray-500">{{ __('Folders') }}</span>
				<Button
					variant="ghost"
					class="!h-7 !w-7 !p-1"
					:title="__('New Folder')"
					@click="startCreatingFolder"
				>
					<Plus class="h-4 w-4" />
				</Button>
			</div>

			<div class="space-y-0.5">
				<button
					class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-gray-100"
					:class="{ 'bg-gray-200 font-medium': selectedFolder === 'favorites' }"
					@click="selectedFolder = 'favorites'"
				>
					<Star class="h-4 w-4 text-gray-500" stroke-width="1.5" />
					<span class="flex-1 truncate text-left">{{ __('Favorites') }}</span>
					<span class="w-5 text-right text-xs text-gray-500">
						{{ store.favorites.length }}
					</span>
				</button>
				<button
					class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-gray-100"
					:class="{ 'bg-gray-200 font-medium': selectedFolder === 'all' }"
					@click="selectedFolder = 'all'"
				>
					<FolderOpen class="h-4 w-4 text-gray-500" stroke-width="1.5" />
					<span class="flex-1 truncate text-left">{{ __('All Dashboards') }}</span>
					<span class="w-5 text-right text-xs text-gray-500">
						{{ store.dashboards.length }}
					</span>
				</button>
			</div>

			<div class="my-2 border-t" />

			<div v-if="creatingFolder" class="mb-1 flex items-center gap-1 px-1">
				<input
					ref="folderInput"
					v-model="folderTitle"
					:maxlength="MAX_FOLDER_TITLE_LENGTH"
					class="h-7 min-w-0 flex-1 rounded border bg-white px-2 text-sm outline-none focus:border-gray-500"
					:placeholder="__('Folder name')"
					@keydown.enter="createFolder"
					@keydown.esc="creatingFolder = false"
				/>
				<button class="rounded p-1 hover:bg-gray-200" @click="createFolder">
					<Check class="h-3.5 w-3.5" />
				</button>
				<button class="rounded p-1 hover:bg-gray-200" @click="creatingFolder = false">
					<X class="h-3.5 w-3.5" />
				</button>
			</div>

			<div class="min-h-0 flex-1 space-y-0.5 overflow-auto">
				<div
					v-for="folder in store.folders"
					:key="folder.name"
					class="group flex items-center gap-1 rounded px-2 py-0.5 hover:bg-gray-100"
					:class="{
						'bg-gray-200': selectedFolder === folder.name,
						'bg-blue-50': dragOverFolder === folder.name,
					}"
					draggable="true"
					@dragstart="startFolderDrag($event, folder)"
					@dragend="finishDrag"
					@dragover="allowFolderDrop($event, folder.name)"
					@dragleave="dragOverFolder = undefined"
					@drop.prevent="
						draggedFolder ? dropFolderBefore(folder) : dropOnFolder(folder.name)
					"
				>
					<GripVertical class="h-3.5 w-3.5 shrink-0 cursor-grab text-gray-400" />
					<Folder class="h-4 w-4 shrink-0 text-gray-500" stroke-width="1.5" />
					<input
						v-if="editingFolder === folder.name"
						v-model="folderTitle"
						:maxlength="MAX_FOLDER_TITLE_LENGTH"
						:data-folder-input="folder.name"
						class="h-7 min-w-0 flex-1 rounded border bg-white px-1.5 text-sm outline-none"
						@keydown.enter="renameFolder(folder)"
						@keydown.esc="editingFolder = undefined"
						@blur="renameFolder(folder)"
					/>
					<button
						v-else
						class="min-w-0 flex-1 truncate py-1 text-left text-sm"
						@click="selectedFolder = folder.name"
					>
						{{ folder.title }}
					</button>
					<span class="w-5 text-right text-xs text-gray-500 group-hover:hidden">
						{{
							store.dashboards.filter((dashboard) => dashboard.folder === folder.name)
								.length
						}}
					</span>
					<div class="hidden items-center group-hover:flex">
						<button
							class="rounded p-1 hover:bg-gray-200"
							:title="__('Rename')"
							@click="startRenaming(folder)"
						>
							<Pencil class="h-3.5 w-3.5" />
						</button>
						<button
							class="rounded p-1 hover:bg-gray-200"
							:title="__('Delete')"
							@click="deleteFolder(folder)"
						>
							<Trash2 class="h-3.5 w-3.5 text-red-600" />
						</button>
					</div>
				</div>
			</div>
		</aside>

		<main class="min-w-0 flex-1 overflow-auto px-5 py-3">
			<div class="mb-5 flex items-center justify-between gap-4">
				<div>
					<h2 class="text-lg font-semibold text-gray-700">{{ selectedTitle }}</h2>
					<p class="mt-1 text-sm text-gray-500">
						{{ __('{0} dashboards', String(filteredDashboards.length)) }}
					</p>
				</div>
				<FormControl
					class="w-64"
					:placeholder="__('Search')"
					v-model="searchQuery"
					:debounce="300"
				>
					<template #prefix>
						<SearchIcon class="h-4 w-4 text-gray-500" />
					</template>
				</FormControl>
			</div>

			<div
				v-if="filteredDashboards.length"
				class="grid grid-cols-1 gap-10 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
			>
				<div
					v-for="dashboard in filteredDashboards"
					:key="dashboard.name"
					draggable="true"
					@dragstart="startDashboardDrag($event, dashboard)"
					@dragend="finishDrag"
				>
					<DashboardCard
						:dashboard="dashboard"
						:dropdown-options="dropdownOptions(dashboard)"
						:folder-title="getFolderTitle(dashboard)"
						:preview-loading="store.updatingPreviewImage[dashboard.name]"
						@toggle-favorite="toggleFavorite(dashboard)"
						@update-preview="store.updatePreviewImage(dashboard.name)"
					/>
				</div>
			</div>

			<div v-else class="flex h-64 w-full flex-col items-center justify-center text-base">
				<div class="text-xl font-medium">{{ __('No Dashboards') }}</div>
				<div class="mt-1 text-base text-gray-600">
					{{ __('Drag dashboards into this folder or create one in a workbook.') }}
				</div>
			</div>
		</main>
	</div>
</template>
