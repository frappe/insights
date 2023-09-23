<script setup lang="jsx">
import ListView from '@/components/ListView.vue'
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import useNotebook from '@/notebook/useNotebook'
import useNotebooks from '@/notebook/useNotebooks'
import { updateDocumentTitle } from '@/utils'
import { ListRow, ListRowItem } from 'frappe-ui'
import { PlusIcon } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({ notebook: String })
const router = useRouter()
const notebook = useNotebook(props.notebook)
notebook.reload()

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
	<ListView
		:columns="[
			{ label: 'Title', name: 'title' },
			{ label: 'Created', name: 'created_from_now' },
			{ label: 'Modified', name: 'modified_from_now' },
		]"
		:rows="notebook.pages"
	>
		<template #actions>
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
		</template>

		<template #list-row="{ row: page }">
			<ListRow
				as="router-link"
				:row="page"
				:to="{
					name: 'NotebookPage',
					params: { notebook: notebook.doc.name, name: page.name },
				}"
			>
				<ListRowItem>
					<FeatherIcon name="file-text" class="h-4 w-4 text-gray-600" />
					<span class="ml-3">{{ page.title }}</span>
				</ListRowItem>
				<ListRowItem> {{ page.created_from_now }} </ListRowItem>
				<ListRowItem> {{ page.modified_from_now }} </ListRowItem>
			</ListRow>
		</template>

		<template #emptyState>
			<div class="text-xl font-medium">No pages.</div>
			<div class="mt-1 text-base text-gray-600">No pages to display.</div>
			<Button
				class="mt-4"
				label="New Page"
				variant="solid"
				@click="() => createNotebookPage()"
			/>
		</template>
	</ListView>

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
