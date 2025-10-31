<script setup lang="ts">
import { ChevronDown, ChevronRight, Plus, X , Folder, PenLine } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
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
const renameFolderInput = ref<HTMLInputElement | null>(null)

function startRenameFolder(folder: WorkbookFolder, event: Event) {
	event.stopPropagation()
	editingFolderName.value = folder.name
	editingFolderTitle.value = folder.title
	// Focus input on next tick
	setTimeout(() => {
		const input = document.querySelector(`input[data-folder="${folder.name}"]`) as HTMLInputElement
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

const draggedItem = ref<{ type: string; item: any; folder?: string } | null>(null)
const dragOverFolder = ref<string | null>(null)
const dragOverItem = ref<string | null>(null)
const dragPosition = ref<'before' | 'after' | null>(null)

function setDraggedItem(event: DragEvent, row: any, folder?: string) {
	if (!event.dataTransfer) return
	draggedItem.value = { type: section.type, item: row, folder }
	const data = JSON.stringify(draggedItem.value)
	event.dataTransfer.setData('text/plain', data)
	event.dataTransfer.effectAllowed = 'move'

	const target = event.currentTarget as HTMLElement
	target.classList.add('dragging')
}

function onDragEnd(event: DragEvent) {
	const target = event.currentTarget as HTMLElement
	target.classList.remove('dragging')
	draggedItem.value = null
	dragOverFolder.value = null
	dragOverItem.value = null
	dragPosition.value = null
}

function onDragOverItem(event: DragEvent, item: any) {
	if (!draggedItem.value || draggedItem.value.type !== section.type) return
	if (draggedItem.value.item.name === item.name) return

	event.preventDefault()
	const target = event.currentTarget as HTMLElement
	const rect = target.getBoundingClientRect()
	const midpoint = rect.top + rect.height / 2

	if (event.clientY < midpoint) {
		dragPosition.value = 'before'
	} else {
		dragPosition.value = 'after'
	}
	dragOverItem.value = item.name
}

function onDragLeaveItem() {
	dragOverItem.value = null
	dragPosition.value = null
}

function onDropOnItem(event: DragEvent, targetItem: any, targetFolder?: string) {
	event.preventDefault()
	event.stopPropagation()

	if (!draggedItem.value || draggedItem.value.type !== section.type) return
	if (draggedItem.value.item.name === targetItem.name) {
		dragOverItem.value = null
		dragPosition.value = null
		return
	}

	const targetContext = targetFolder
		? folderItems.value[targetFolder] || []
		: rootItems.value

	const draggedItemName = draggedItem.value.item.name
	const targetIdx = targetContext.findIndex((i) => i.name === targetItem.name)

	// remove dragged item from context(if it exists)
	const contextWithoutDragged = targetContext.filter(i => i.name !== draggedItemName)
	let insertIdx = targetIdx

	// adjust insert index if the dragged item was before the target
	const draggedIdx = targetContext.findIndex(i => i.name === draggedItemName)
	if (draggedIdx !== -1 && draggedIdx < targetIdx) {
		insertIdx--
	}

	if (dragPosition.value === 'after') {
		insertIdx++
	}
	const newOrder = [...contextWithoutDragged]
	newOrder.splice(insertIdx, 0, { name: draggedItemName })

	const updates = newOrder.map((item, index) => ({
		type: section.type,
		name: item.name,
		sort_order: index,
		folder: targetFolder || null
	}))

	workbook.updateSortOrder(updates).then(() => {
		workbook.load()
	})

	dragOverItem.value = null
	dragPosition.value = null
}

function onDragEnterFolder(event: DragEvent, folder: WorkbookFolder) {
	event.stopPropagation()
	if (draggedItem.value?.type === section.type) {
		dragOverFolder.value = folder.name
	}
}

function onDragLeaveFolder(event: DragEvent) {
	const relatedTarget = event.relatedTarget as HTMLElement
	const currentTarget = event.currentTarget as HTMLElement

	if (relatedTarget && currentTarget.contains(relatedTarget)) {
		return
	}

	dragOverFolder.value = null
}

function onDropFolder(event: DragEvent, targetFolder: WorkbookFolder) {
	event.preventDefault()
	event.stopPropagation()
	dragOverFolder.value = null

	if (!draggedItem.value || draggedItem.value.type !== section.type) return
	const targetFolderId = targetFolder.name

	//move if not already in this folder
	if (draggedItem.value.item.folder === targetFolderId) {
		return
	}

	const itemsInFolder = folderItems.value[targetFolderId] || []
	// place at the end of the folder
	let newSortOrder = 0
	if (itemsInFolder.length > 0) {
		const lastItem = itemsInFolder[itemsInFolder.length - 1]
			newSortOrder = lastItem.sort_order + 1
	}

	const updates = [{
		type: section.type,
		name: draggedItem.value.item.name,
		sort_order: newSortOrder,
		folder: targetFolderId
	}]

	workbook.updateSortOrder(updates).then(() => {
		workbook.load()
		})
}

function allowDrop(event: DragEvent) {
	event.preventDefault()
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
				<Folder class="h-4 w-4 text-gray-600" stroke-width="1.5" />
				</Button>
				<Button 
					class="!h-fit !p-1" 
					variant="ghost" 
					@click="section.add()">
				<Plus class="h-4 w-4 text-gray-600" stroke-width="1.5" />
				</Button>
			</div>
		</div>

		<div
			v-if="!section.items.length && !folders.length"
			class="flex h-12 flex-col items-center justify-center rounded border border-dashed border-gray-300 py-2"
		>
			<div class="text-xs text-gray-500">{{ section.emptyMessage }}</div>
		</div>

		<div v-else class="flex flex-col border-b pb-3">
			<div
				v-for="row in rootItems"
				:key="row.name"
				class="relative"
			>
				<div
					v-if="dragOverItem === row.name && dragPosition === 'before'"
					class="absolute -top-0.5 left-0 right-0 h-0.5 bg-blue-500 transition-all"
				/>

				<div
					class="group w-full cursor-pointer rounded transition-all hover:bg-gray-100 drag-item"
					:class="[
						section.isActive(row) ? ' bg-gray-100' : '',
						dragOverItem === row.name ? 'bg-blue-50' : ''
					]"
					draggable="true"
					@dragstart="setDraggedItem($event, row)"
					@dragend="onDragEnd"
					@dragover="onDragOverItem($event, row)"
					@dragleave="onDragLeaveItem"
					@drop="onDropOnItem($event, row)"
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
							class="invisible cursor-pointer rounded px-1.5 py-1 transition-all hover:bg-gray-100 group-hover:visible"
							@click.prevent.stop="section.remove(row)"
						>
							<X class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</button>
					</router-link>
				</div>

				<div
					v-if="dragOverItem === row.name && dragPosition === 'after'"
					class="absolute -bottom-0.5 left-0 right-0 h-0.5 bg-blue-500 transition-all"
				/>
			</div>

			<div
				v-for="folder in sortedFolders"
				:key="folder.name"
				class="mt-1 rounded transition-all"
				:class="{
					'bg-blue-50 ring-1 ring-blue-400': dragOverFolder === folder.name
				}"
			>
				<div
					:class="['group flex h-7.5 cursor-pointer items-center justify-between rounded px-1.5 mb-0.5 transition-all hover:bg-gray-100', 
					editingFolderName === folder.name ? 'ring-1 ring-gray-400' : '']"
					@click="editingFolderName !== folder.name && toggleFolder(folder)"
					@dragenter="onDragEnterFolder($event, folder)"
					@dragleave="onDragLeaveFolder"
					@drop="onDropFolder($event, folder)"
					@dragover="allowDrop"
				>
					<div class="flex items-center gap-1.5 overflow-hidden">
						<ChevronRight
							v-if="!isFolderExpanded(folder.name) && editingFolderName !== folder.name"
							class="h-4 w-4 flex-shrink-0 text-gray-600"
							stroke-width="1.5"
						/>
						<ChevronDown
							v-else-if="isFolderExpanded(folder.name) && editingFolderName !== folder.name"
							class="h-4 w-4 flex-shrink-0 text-gray-600"
							stroke-width="1.5"
						/>
						<input
							v-if="editingFolderName === folder.name"
							v-model="editingFolderTitle"
							:data-folder="folder.name"
							class="flex-1 truncate text-sm outline-none border-none bg-transparent w-full "
							@click.stop
							@blur="finishRenameFolder(folder)"
							@keydown.enter="finishRenameFolder(folder)"
							@keydown.esc="editingFolderName = null"
						/>
						<p v-else class="flex-1 truncate text-sm">{{ folder.title }}</p>
					</div>
					<div v-if="editingFolderName !== folder.name" class="invisible flex gap-0.5 group-hover:visible">
						<button
							class="cursor-pointer rounded p-1 transition-all hover:bg-gray-200"
							@click.stop="startRenameFolder(folder, $event)"
						>
							<PenLine class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
						</button>
						<button
							class="cursor-pointer rounded p-1 transition-all hover:bg-gray-200"
							@click.stop="removeFolder(folder, $event)"
						>
							<X class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
						</button>
					</div>
				</div>

				<div
					v-if="isFolderExpanded(folder.name) && folderItems[folder.name]"
					class="ml-3 rounded"
					@dragenter="onDragEnterFolder($event, folder)"
					@dragleave="onDragLeaveFolder"
					@drop="onDropFolder($event, folder)"
					@dragover="allowDrop"
				>
					<div
						v-for="row in folderItems[folder.name]"
						:key="row.name"
						class="relative"
					>
						<div
							v-if="dragOverItem === row.name && dragPosition === 'before'"
							class="absolute -top-0.5 left-0 right-0 h-0.5 bg-blue-500 transition-all"
						/>

						<div
							class="group w-full cursor-pointer rounded transition-all hover:bg-gray-100 drag-item"
							:class="[
								section.isActive(row) ? ' bg-gray-100' : '',
								dragOverItem === row.name ? 'bg-blue-50' : ''
							]"
							draggable="true"
							@dragstart="setDraggedItem($event, row, folder.name)"
							@dragend="onDragEnd"
							@dragover="onDragOverItem($event, row)"
							@dragleave="onDragLeaveItem"
							@drop="onDropOnItem($event, row, folder.name)"
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
									class="invisible cursor-pointer rounded px-1.5 py-1 transition-all hover:bg-gray-100 group-hover:visible"
									@click.prevent.stop="section.remove(row)"
								>
									<X class="h-4 w-4 text-gray-700" stroke-width="1.5" />
								</button>
							</router-link>
						</div>

						<div
							v-if="dragOverItem === row.name && dragPosition === 'after'"
							class="absolute -bottom-0.5 left-0 right-0 h-0.5 bg-blue-500 transition-all"
						/>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.drag-item.dragging {
	opacity: 0.4;
	transform: scale(0.98);
}

.drag-item {
	transition:
		opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1),
		transform 0.2s cubic-bezier(0.4, 0, 0.2, 1),
		background-color 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>
