import { Ref } from 'vue'
import { confirmDialog } from '../helpers/confirm_dialog'
import { __ } from '../translation'
import useWorkbookFolders from './workbookFolders'

type FolderStore = ReturnType<typeof useWorkbookFolders>
type FolderRef = { name: string; title: string }

// Admin-facing folder CRUD, wrapped as confirm dialogs. `refresh` is run after a
// successful change; new folders are created inside `currentFolder`.
export function useFolderActions(
	folderStore: FolderStore,
	refresh: () => void,
	currentFolder: Ref<string | null>,
) {
	function openNewFolder() {
		confirmDialog({
			title: __('New Folder'),
			primaryActionLabel: __('Create'),
			fields: [
				{ fieldname: 'title', label: __('Title'), placeholder: __('Folder name'), required: true },
			],
			onSuccess: ({ values }: any) => {
				if (!values.title) return
				return folderStore.createFolder(values.title, currentFolder.value).then(refresh)
			},
		})
	}

	function renameFolder(folder: FolderRef) {
		confirmDialog({
			title: __('Rename Folder'),
			primaryActionLabel: __('Rename'),
			fields: [
				{ fieldname: 'title', label: __('Title'), placeholder: folder.title, required: true },
			],
			onSuccess: ({ values }: any) => {
				if (!values.title) return
				return folderStore.renameFolder(folder.name, values.title).then(refresh)
			},
		})
	}

	function deleteFolder(folder: FolderRef) {
		confirmDialog({
			title: __('Delete Folder'),
			message: __('Delete "{0}"? The folder must be empty first.', folder.title),
			theme: 'red',
			primaryActionLabel: __('Delete'),
			onSuccess: () => folderStore.deleteFolder(folder.name).then(refresh),
		})
	}

	return { openNewFolder, renameFolder, deleteFolder }
}
