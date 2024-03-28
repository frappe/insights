<script setup lang="jsx">
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import useNotebook from '@/notebook/useNotebook'
import useNotebooks from '@/notebook/useNotebooks'
import { updateDocumentTitle } from '@/utils'
import { ListView } from 'frappe-ui'
import { PlusIcon, SearchIcon } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({ notebook: String })
const router = useRouter()
const notebook = useNotebook(props.notebook)
notebook.reload()
const searchQuery = ref('')

async function createNotebookPage() {
	const page_name = await notebook.createPage(props.notebook)
	router.push({
		name: 'NotebookPage',
		params: {
			notebook: props.notebook,
			name: page_name,
		},
	})
}

const showDeleteDialog = ref(false)
async function handleDelete() {
	await notebook.deleteNotebook()
	showDeleteDialog.value = false
	await useNotebooks().reload()
	router.push({ name: 'NotebookList' })
}

const pageMeta = ref({ title: 'Notebook' })
updateDocumentTitle(pageMeta)
</script>

<template>
	<header class="sticky top-0 z-10 flex items-center justify-between bg-white px-5 py-2.5">
		<PageBreadcrumbs
			class="h-7"
			:items="[
				{ label: 'Notebooks', route: { path: '/notebook' } },
				{ label: notebook.doc.title || notebook.doc.name },
			]"
		/>
		<div class="space-x-2.5">
			<Button label="New Page" variant="solid" @click="() => createNotebookPage()">
				<template #prefix>
					<PlusIcon class="w-4" />
				</template>
			</Button>
		</div>
	</header>

	<div class="mb-4 flex h-full flex-col gap-2 overflow-auto px-4">
		<div class="flex gap-2 overflow-visible py-1">
			<FormControl placeholder="Search by Title" v-model="searchQuery" :debounce="300">
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" />
				</template>
			</FormControl>
			<Dropdown
				placement="left"
				:button="{ icon: 'more-horizontal', variant: 'ghost' }"
				:options="[
					{
						label: 'Delete',
						icon: 'trash-2',
						onClick: () => (showDeleteDialog = true),
					},
				]"
			/>
		</div>
		<ListView
			:columns="[
				{ label: 'Title', key: 'title' },
				{ label: 'Created', key: 'created_from_now' },
				{ label: 'Modified', key: 'modified_from_now' },
			]"
			:rows="notebook.pages"
			:row-key="'name'"
			:options="{
				showTooltip: false,
				getRowRoute: (page) => ({
					name: 'NotebookPage',
					params: { notebook: notebook.doc.name, name: page.name },
				}),
				emptyState: {
					title: 'No pages.',
					description: 'No pages to display.',
					button: {
						label: 'New Page',
						variant: 'solid',
						onClick: () => createNotebookPage(),
					},
				},
			}"
		>
		</ListView>
	</div>

	<Dialog
		:options="{
			title: 'Delete Notebook',
			icon: { name: 'trash', variant: 'solid', theme: 'red' },
		}"
		v-model="showDeleteDialog"
		:dismissable="true"
	>
		<template #body-content>
			<p class="text-base text-gray-600">Are you sure you want to delete this notebook?</p>
		</template>
		<template #actions>
			<Button variant="outline" @click="showDeleteDialog = false">Cancel</Button>
			<Button variant="solid" theme="red" @click="handleDelete" :loading="notebook.deleting">
				Yes
			</Button>
		</template>
	</Dialog>
</template>
