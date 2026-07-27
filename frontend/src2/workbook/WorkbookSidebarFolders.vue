<script setup lang="ts">
import { Folder, FolderOpen, FolderPlus, PenLine, Plus, X } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import Draggable from 'vuedraggable'
import type { WorkbookChart, WorkbookFolder, WorkbookQuery } from '../types/workbook.types'
import { workbookKey } from './workbook'

const section = defineProps<{
	title: string
	emptyMessage: string
	items: (WorkbookQuery | WorkbookChart)[]
	itemKey: string
	isActive: (item: any) => boolean
	add: () => void
	remove: (item: any) => void
	route: (item: any) => string
	type: 'query' | 'chart'
}>()

const workbook = inject(workbookKey)!

// One shared group so items can be dragged freely between the root list and
// any folder list of the same section type.
const dragGroup = computed(() => `${section.type}-items`)

const folders = computed(() => {
	return (workbook.doc.folders || []).filter((f) => f.type === section.type)
})

const rootItems = computed(() => {
	return section.items.filter((item) => !item.folder).sort((a, b) => a.sort_order - b.sort_order)
})

const folderItems = computed(() => {
	const result: Record<string, typeof section.items> = {}
	section.items.forEach((item) => {
		if (item.folder) {
			if (!result[item.folder]) {
				result[item.folder] = []
			}
			result[item.folder].push(item)
		}
	})
	Object.keys(result).forEach((folderId) => {
		result[folderId].sort((a, b) => a.sort_order - b.sort_order)
	})
	return result
})

const sortedFolders = computed(() => {
	return [...folders.value].sort((a, b) => a.sort_order - b.sort_order)
})

const expandedFolders = ref<Set<string>>(new Set())

function toggleFolder(folder: WorkbookFolder) {
	if (expandedFolders.value.has(folder.name)) {
		expandedFolders.value.delete(folder.name)
	} else {
		expandedFolders.value.add(folder.name)
	}
}

function isFolderExpanded(folderName: string) {
	return expandedFolders.value.has(folderName)
}

function removeFolder(folder: WorkbookFolder, event: Event) {
	event.stopPropagation()
	workbook.removeFolder(folder.name)
}

const editingFolderName = ref<string | null>(null)
const editingFolderTitle = ref('')

function startRenameFolder(folder: WorkbookFolder, event: Event) {
	event.stopPropagation()
	editingFolderName.value = folder.name
	editingFolderTitle.value = folder.title
	// Focus input on next tick
	setTimeout(() => {
		const input = document.querySelector(
			`input[data-folder="${folder.name}"]`,
		) as HTMLInputElement
		if (input) {
			input.focus()
			input.select()
		}
	}, 0)
}

function finishRenameFolder(folder: WorkbookFolder) {
	if (editingFolderTitle.value && editingFolderTitle.value !== folder.title) {
		workbook.renameFolder(folder.name, editingFolderTitle.value)
		folder.title = editingFolderTitle.value
	}
	editingFolderName.value = null
}

// vuedraggable emits `change` with one of moved/added/removed. We rebuild the
// affected list's order from that event, write sort_order + folder onto the
// (shared) item objects so the computeds re-derive without a snap-back, and
// persist. A cross-list move fires `removed` on the source and `added` on the
// target; we persist only from the `added` (and same-list `moved`) side, which
// already carries the moved item with its new folder. The `removed` side is
// ignored so we don't issue a second, racing write for the source list.
function onListChange(
	currentList: (WorkbookQuery | WorkbookChart)[],
	event: any,
	folderName: string | null,
) {
	const list = [...currentList]
	if (event.moved) {
		const [moved] = list.splice(event.moved.oldIndex, 1)
		list.splice(event.moved.newIndex, 0, moved)
	} else if (event.added) {
		list.splice(event.added.newIndex, 0, event.added.element)
	} else {
		return
	}

	const updates = list.map((item, index) => {
		item.sort_order = index
		item.folder = folderName
		return { type: section.type, name: item.name, sort_order: index, folder: folderName }
	})

	workbook.updateSortOrder(updates)
}
</script>

<template>
	<div class="flex flex-col px-3.5 pt-3">
		<div class="mb-1 flex h-6 items-center justify-between">
			<div class="flex items-center gap-1">
				<div class="text-sm font-medium">{{ section.title }}</div>
			</div>
			<div v-if="!editingFolderName" class="flex gap-1">
				<Button
					class="!h-fit !p-1"
					variant="ghost"
					@click="workbook.addFolder(`Untitled`, section.type)"
				>
					<FolderPlus class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
				</Button>
				<Button class="!h-fit !p-1" variant="ghost" @click="section.add()">
					<Plus class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
				</Button>
			</div>
		</div>

		<div
			v-if="!section.items.length && !folders.length"
			class="flex h-12 flex-col items-center justify-center rounded border border-dashed border-outline-gray-2 py-2"
		>
			<div class="text-xs text-ink-gray-4">{{ section.emptyMessage }}</div>
		</div>

		<div v-else class="flex flex-col border-b pb-3">
			<Draggable
				:model-value="rootItems"
				:group="dragGroup"
				item-key="name"
				class="min-h-6"
				:animation="150"
				:delay="150"
				:delay-on-touch-only="true"
				:touch-start-threshold="5"
				:empty-insert-threshold="20"
				ghost-class="sortable-ghost"
				chosen-class="sortable-chosen"
				@change="(e: any) => onListChange(rootItems, e, null)"
			>
				<template #item="{ element: row }">
					<div
						class="group w-full cursor-pointer rounded transition-all hover:bg-surface-gray-2"
						:class="section.isActive(row) ? 'bg-surface-gray-3' : ''"
					>
						<router-link
							:to="route(row)"
							class="flex h-7.5 items-center justify-between rounded pl-1.5 text-sm"
						>
							<div class="flex gap-1.5 overflow-hidden">
								<div class="flex-shrink-0">
									<slot name="item-icon" :item="row" />
								</div>
								<p class="truncate">{{ row.title }}</p>
							</div>
							<button
								class="invisible cursor-pointer rounded px-1.5 py-1 transition-all hover:bg-surface-gray-3 group-hover:visible"
								@click.prevent.stop="section.remove(row)"
							>
								<X class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
							</button>
						</router-link>
					</div>
				</template>
			</Draggable>

			<div v-for="folder in sortedFolders" :key="folder.name" class="rounded transition-all">
				<Draggable
					:model-value="folderItems[folder.name] || []"
					:group="dragGroup"
					item-key="name"
					class="drop-folder"
					:animation="150"
					:delay="150"
					:delay-on-touch-only="true"
					:touch-start-threshold="5"
					:empty-insert-threshold="20"
					ghost-class="sortable-ghost"
					chosen-class="sortable-chosen"
					@change="
						(e: any) => onListChange(folderItems[folder.name] || [], e, folder.name)
					"
				>
					<template #header>
						<div
							:class="[
								'folder-header group flex h-7.5 cursor-pointer items-center justify-between rounded px-1.5 transition-all hover:bg-surface-gray-2',
								editingFolderName === folder.name
									? 'ring-1 ring-outline-gray-3'
									: '',
							]"
							@click="editingFolderName !== folder.name && toggleFolder(folder)"
						>
							<div class="flex items-center gap-1.5 overflow-hidden">
								<FolderOpen
									v-if="isFolderExpanded(folder.name)"
									class="h-4 w-4 flex-shrink-0 text-ink-gray-5"
									stroke-width="1.5"
								/>
								<Folder
									v-else
									class="h-4 w-4 flex-shrink-0 text-ink-gray-5"
									stroke-width="1.5"
								/>
								<input
									v-if="editingFolderName === folder.name"
									v-model="editingFolderTitle"
									:data-folder="folder.name"
									class="flex-1 truncate text-sm outline-none border-none bg-transparent w-full"
									@click.stop
									@blur="finishRenameFolder(folder)"
									@keydown.enter="finishRenameFolder(folder)"
									@keydown.esc="editingFolderName = null"
								/>
								<p v-else class="flex-1 truncate text-sm">{{ folder.title }}</p>
							</div>
							<div
								v-if="editingFolderName !== folder.name"
								class="invisible flex gap-0.5 group-hover:visible"
							>
								<button
									class="cursor-pointer rounded p-1 transition-all hover:bg-surface-gray-3"
									@click.stop="startRenameFolder(folder, $event)"
								>
									<PenLine
										class="h-3.5 w-3.5 text-ink-gray-6"
										stroke-width="1.5"
									/>
								</button>
								<button
									class="cursor-pointer rounded p-1 transition-all hover:bg-surface-gray-3"
									@click.stop="removeFolder(folder, $event)"
								>
									<X class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
								</button>
							</div>
						</div>
					</template>

					<template #footer>
						<div
							v-if="
								isFolderExpanded(folder.name) && !folderItems[folder.name]?.length
							"
							class="ml-[22px] flex h-7.5 items-center pl-1.5 text-sm text-ink-gray-3"
						>
							{{ __('Empty') }}
						</div>
					</template>

					<template #item="{ element: row }">
						<div v-show="isFolderExpanded(folder.name)" class="ml-[22px]">
							<div
								class="group w-full cursor-pointer rounded transition-all hover:bg-surface-gray-2"
								:class="section.isActive(row) ? 'bg-surface-gray-3' : ''"
							>
								<router-link
									:to="route(row)"
									class="flex h-7.5 items-center justify-between rounded pl-1.5 text-sm"
								>
									<div class="flex gap-1.5 overflow-hidden">
										<div class="flex-shrink-0">
											<slot name="item-icon" :item="row" />
										</div>
										<p class="truncate">{{ row.title }}</p>
									</div>
									<button
										class="invisible cursor-pointer rounded px-1.5 py-1 transition-all hover:bg-surface-gray-3 group-hover:visible"
										@click.prevent.stop="section.remove(row)"
									>
										<X class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
									</button>
								</router-link>
							</div>
						</div>
					</template>
				</Draggable>
			</div>
		</div>
	</div>
</template>

<style scoped>
.sortable-ghost {
	@apply rounded bg-surface-gray-3 opacity-60;
}

.sortable-chosen {
	@apply opacity-90;
}

/* Highlight the whole folder while a dragged item hovers inside it, so dropping
   reads as "into this folder" rather than "below it" — the placeholder alone is
   ambiguous, especially when the folder is collapsed (where v-show already hides
   the placeholder, leaving the header highlight as the only drop-target signal). */
.drop-folder:has(.sortable-ghost) .folder-header {
	@apply bg-surface-gray-3 ring-1 ring-outline-gray-3;
}
</style>
