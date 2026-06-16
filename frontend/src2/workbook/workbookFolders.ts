import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { showErrorToast } from '../helpers'
import { createSuccessToast } from '../helpers/toasts'
import { __ } from '../translation'
import { WorkbookFolderItem } from '../types/workbook.types'

const folders = ref<WorkbookFolderItem[]>([])

async function getFolders() {
	folders.value = await call('insights.api.workbooks.get_workbook_folders')
	return folders.value
}

async function createFolder(title: string, parent_folder?: string | null) {
	return call('insights.api.workbooks.create_workbook_folder', {
		title,
		parent_folder: parent_folder || null,
	})
		.then((name: string) => {
			createSuccessToast(__('Folder created'))
			return getFolders().then(() => name)
		})
		.catch(showErrorToast)
}

async function renameFolder(folder_name: string, new_title: string) {
	return call('insights.api.workbooks.rename_workbook_folder', { folder_name, new_title })
		.then(() => {
			createSuccessToast(__('Folder renamed'))
			return getFolders()
		})
		.catch(showErrorToast)
}

async function deleteFolder(folder_name: string) {
	return call('insights.api.workbooks.delete_workbook_folder', { folder_name })
		.then(() => {
			createSuccessToast(__('Folder deleted'))
			return getFolders()
		})
		.catch(showErrorToast)
}

async function moveWorkbookToFolder(workbook: string, folder?: string | null) {
	return call('insights.api.workbooks.move_workbook_to_folder', {
		workbook,
		folder: folder || null,
	})
		.then(() => createSuccessToast(__('Workbook moved')))
		.catch(showErrorToast)
}

async function moveWorkbooksToFolder(workbooks: string[], folder?: string | null) {
	return call('insights.api.workbooks.move_workbooks_to_folder', {
		workbooks,
		folder: folder || null,
	})
		.then((moved: number) =>
			createSuccessToast(
				moved === 1 ? __('1 workbook moved') : __('{0} workbooks moved', String(moved)),
			),
		)
		.catch(showErrorToast)
}

export default function useWorkbookFolders() {
	if (!folders.value.length) {
		getFolders()
	}
	return reactive({
		folders,
		getFolders,
		createFolder,
		renameFolder,
		deleteFolder,
		moveWorkbookToFolder,
		moveWorkbooksToFolder,
	})
}

// ---- client-side tree helpers (folder navigation is derived, not fetched) ----

export function childrenOf(allFolders: WorkbookFolderItem[], parent: string | null) {
	return allFolders.filter((f) => (f.parent_folder || null) === parent)
}

export function folderBreadcrumb(allFolders: WorkbookFolderItem[], current: string | null) {
	const byName = Object.fromEntries(allFolders.map((f) => [f.name, f]))
	const trail: { name: string; title: string }[] = []
	let cursor = current
	while (cursor && byName[cursor]) {
		const node = byName[cursor]
		trail.unshift({ name: node.name, title: node.title })
		cursor = node.parent_folder
	}
	return trail
}

// Build the nested "Move to folder" dropdown options from the folder tree.
// Depth is capped at 2, so a top-level folder may have one submenu level of
// subfolders. Each folder is both a destination ("Move here") and a gateway.
export function buildFolderMoveOptions(
	allFolders: WorkbookFolderItem[],
	currentFolder: string | null,
	onMove: (folder: string | null) => void,
) {
	const topLevel = allFolders.filter((f) => !f.parent_folder)

	const options: any[] = [
		{
			label: __('Top level'),
			disabled: !currentFolder,
			onClick: () => onMove(null),
		},
	]

	for (const folder of topLevel) {
		const children = childrenOf(allFolders, folder.name)
		if (children.length) {
			options.push({
				label: folder.title,
				submenu: [
					{
						label: __('Move to {0}', folder.title),
						disabled: currentFolder === folder.name,
						onClick: () => onMove(folder.name),
					},
					...children.map((child) => ({
						label: child.title,
						disabled: currentFolder === child.name,
						onClick: () => onMove(child.name),
					})),
				],
			})
		} else {
			options.push({
				label: folder.title,
				disabled: currentFolder === folder.name,
				onClick: () => onMove(folder.name),
			})
		}
	}

	return options
}
