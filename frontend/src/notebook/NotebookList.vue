<script setup lang="jsx">
import List from '@/components/List.vue'
import { updateDocumentTitle } from '@/utils'
import { useRouter } from 'vue-router'
import useNotebooks from '@/notebook/useNotebooks'
import { ref } from 'vue'

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
			name: uncategorized.name,
			page: page_name,
		},
	})
}

const pageMeta = ref({ title: 'Notebooks' })
updateDocumentTitle(pageMeta)
</script>

<template>
	<div class="h-full w-full bg-white px-8 py-4">
		<List
			title="Notebooks"
			:actions="[
				{
					label: 'Notebook',
					appearance: 'white',
					iconLeft: 'plus',
					handler: () => (new_notebook_dialog = true),
				},
				{
					label: 'Notebook Page',
					appearance: 'white',
					iconLeft: 'plus',
					handler: () => createNotebookPage(),
				},
			]"
			:columns="columns"
			:data="notebooks.list"
			:rowClick="({ name }) => router.push({ name: 'Notebook', params: { name } })"
		>
		</List>
	</div>

	<Dialog :options="{ title: 'New Dashboard' }" v-model="new_notebook_dialog">
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
			<Button appearance="primary" @click="createNotebook" :loading="notebooks.creating">
				Create
			</Button>
		</template>
	</Dialog>
</template>