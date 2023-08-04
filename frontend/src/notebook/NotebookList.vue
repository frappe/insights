<script setup lang="jsx">
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import ListView from '@/components/ListView.vue'
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import useNotebooks from '@/notebook/useNotebooks'
import { updateDocumentTitle } from '@/utils'
import { PlusIcon } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const notebooks = useNotebooks()
notebooks.reload()

const TitleWithIcon = (props) => (
	<div class="flex items-center">
		<FeatherIcon name="folder" class="h-4 w-4 text-gray-600" />
		<span class="ml-3">{props.row.title}</span>
	</div>
)
const columns = [
	{ label: 'Title', key: 'title', cellComponent: TitleWithIcon },
	{ label: 'Created', key: 'created_from_now' },
	{ label: 'Modified', key: 'modified_from_now' },
]

const new_notebook_dialog = ref(false)
const new_notebook_title = ref('')
async function createNotebook() {
	await notebooks.createNotebook(new_notebook_title.value)
	new_notebook_dialog.value = false
	new_notebook_title.value = ''
}

async function createNotebookPage() {
	const uncategorized = notebooks.list.find((notebook) => notebook.title === 'Uncategorized')
	const page_name = await notebooks.createPage(uncategorized.name)
	router.push({
		name: 'NotebookPage',
		params: {
			notebook: uncategorized.name,
			name: page_name,
		},
	})
}

const pageMeta = ref({ title: 'Notebooks' })
updateDocumentTitle(pageMeta)
</script>

<template>
	<header class="sticky top-0 z-10 flex items-center justify-between bg-white px-5 py-2.5">
		<PageBreadcrumbs class="h-7" :items="[{ label: 'Notebooks' }]" />
		<div class="space-x-2.5">
			<Button label="New Notebook" variant="solid" @click="new_notebook_dialog = true">
				<template #prefix>
					<PlusIcon class="w-4" />
				</template>
			</Button>
		</div>
	</header>
	<div class="flex flex-1 overflow-hidden bg-white px-6 py-2">
		<ListView
			:columns="columns"
			:data="notebooks.list"
			:rowClick="({ name }) => router.push({ name: 'Notebook', params: { notebook: name } })"
		>
		</ListView>
	</div>

	<Dialog :options="{ title: 'New Notebook' }" v-model="new_notebook_dialog">
		<template #body-content>
			<div class="space-y-4">
				<Input
					type="text"
					label="Title"
					placeholder="Enter a suitable title..."
					v-model="new_notebook_title"
				/>
			</div>
		</template>
		<template #actions>
			<Button variant="solid" @click="createNotebook" :loading="notebooks.creating">
				Create
			</Button>
		</template>
	</Dialog>
</template>
