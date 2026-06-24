import { computed, ref, Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { WorkbookFolderItem } from '../types/workbook.types'
import { childrenOf, folderBreadcrumb } from './workbookFolders'

// Shared drill-in folder navigation for the workbook and dashboard list pages.
// Navigation is driven by the `?folder=` URL query so the browser back button
// drills up a level; subfolders and breadcrumb are derived from the cached tree.
export function useFolderNavigation(folders: Ref<WorkbookFolderItem[]>, rootLabel: string) {
	const route = useRoute()
	const router = useRouter()

	const currentFolder = computed(() => (route.query.folder as string) || null)
	const searchQuery = ref('')

	function drillInto(folder: string | null) {
		searchQuery.value = ''
		router.push({ query: folder ? { folder } : {} })
	}

	const subfolders = computed(() => childrenOf(folders.value, currentFolder.value))

	const breadcrumbs = computed(() => [
		{ label: rootLabel, onClick: () => drillInto(null) },
		...folderBreadcrumb(folders.value, currentFolder.value).map((b) => ({
			label: b.title,
			onClick: () => drillInto(b.name),
		})),
	])

	return { currentFolder, searchQuery, drillInto, subfolders, breadcrumbs }
}
