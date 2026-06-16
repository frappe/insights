import { Avatar, Dropdown } from 'frappe-ui'
import { Building2, Eye, Folder, Lock, MoreHorizontal, Shield } from 'lucide-vue-next'
import { Ref } from 'vue'
import { __ } from '../translation'
import { WorkbookFolderItem, WorkbookListItem } from '../types/workbook.types'
import useUserStore from '../users/users'
import { buildFolderMoveOptions } from './workbookFolders'

type FolderRef = { name: string; title: string }

type Deps = {
	userStore: ReturnType<typeof useUserStore>
	isAdmin: Ref<boolean>
	folders: Ref<WorkbookFolderItem[]>
	onRenameFolder: (folder: FolderRef) => void
	onDeleteFolder: (folder: FolderRef) => void
	onMoveWorkbook: (workbook: string, folder: string | null) => void
}

const isFolder = (row: any) => row.__type === 'folder'

// Columns for the mixed folder/workbook list. Folder rows only render a title +
// actions; workbook rows render the full set.
export function getWorkbookColumns(deps: Deps) {
	const { userStore, isAdmin, folders, onRenameFolder, onDeleteFolder, onMoveWorkbook } = deps

	return [
		{
			label: __('Title'),
			key: 'title',
			width: 4,
			prefix: ({ row }: any) =>
				isFolder(row) ? <Folder class="h-4 w-4 text-gray-600" stroke-width="1.5" /> : undefined,
		},
		{
			label: __('Access'),
			key: 'shared_with',
			width: 2,
			getLabel: ({ row }: any) => {
				if (isFolder(row)) return ''
				if (row.shared_with_organization) return __('Everyone')
				if (!row.shared_with?.length) return __('Private')
				return row.shared_with.length > 1
					? `${row.shared_with.length} people`
					: userStore.getName(row.shared_with[0])
			},
			prefix: ({ row }: { row: WorkbookListItem & { __type: string } }) => {
				if (isFolder(row)) return
				if (row.shared_with_organization) return <Building2 class="h-3.5 w-3.5 text-blue-500" />
				if (!row.shared_with?.length) return <Lock class="h-3.5 w-3.5 text-orange-500" />
				return <Shield class="h-3.5 w-3.5 text-green-500" />
			},
		},
		{
			label: __('Views'),
			key: 'views',
			width: 1.5,
			getLabel: () => {},
			prefix: ({ row }: any) =>
				isFolder(row) ? undefined : (
					<div class="flex gap-1">
						<Eye class="h-3.5 w-3.5 text-gray-600" stroke-width="1.5" />
						<span class="font-mono text-sm text-gray-700">{row.views}</span>
					</div>
				),
		},
		{
			label: __('Owner'),
			key: 'owner',
			width: 2,
			getLabel: ({ row }: any) =>
				isFolder(row) ? '' : userStore.getUser(row.owner)?.full_name || row.owner,
			prefix: ({ row }: any) => {
				if (isFolder(row)) return
				const user = userStore.getUser(row.owner)
				return <Avatar size="md" label={row.owner} image={user?.user_image} />
			},
		},
		{
			label: __('Modified'),
			key: 'modified_from_now',
			width: 2,
			getLabel: ({ row }: any) => (isFolder(row) ? '' : row.modified_from_now),
		},
		{
			label: '',
			key: 'actions',
			width: 0.5,
			getLabel: () => {},
			prefix: ({ row }: any) => {
				let options: any[] = []
				if (isFolder(row)) {
					if (!isAdmin.value) return
					options = [
						{ label: __('Rename'), icon: 'edit-2', onClick: () => onRenameFolder(row) },
						{ label: __('Delete'), icon: 'trash-2', theme: 'red', onClick: () => onDeleteFolder(row) },
					]
				} else {
					options = [
						{
							group: __('Move to folder'),
							items: buildFolderMoveOptions(folders.value, row.folder ?? null, (folder) =>
								onMoveWorkbook(row.name, folder),
							),
						},
					]
				}
				return (
					<Dropdown options={options} placement="right">
						{{
							default: () => (
								<button
									class="flex h-7 w-7 items-center justify-center rounded hover:bg-gray-100"
									onClick={(e: Event) => e.stopPropagation()}
								>
									<MoreHorizontal class="h-4 w-4 text-gray-600" />
								</button>
							),
						}}
					</Dropdown>
				)
			},
		},
	]
}
