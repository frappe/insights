<script setup lang="jsx">
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import ContentEditable from '@/components/ContentEditable.vue'
import useNotebook from '@/notebook/useNotebook'
import useNotebookPage from '@/notebook/useNotebookPage'
import { updateDocumentTitle } from '@/utils'
import { computed, provide, ref } from 'vue'
import { useRouter } from 'vue-router'
import TipTap from './tiptap/TipTap.vue'

const props = defineProps({
	notebook: String,
	name: String,
})
const page = useNotebookPage(props.name)
const notebook = useNotebook(props.notebook)
provide('page', page)

const show_delete_dialog = ref(false)
const router = useRouter()
function deletePage() {
	page.delete().then(() => {
		router.push(`/notebook/${notebook.doc.name}`)
	})
}

const pageMeta = computed(() => ({
	title: page.doc?.title,
	subtitle: page.doc?.notebook,
}))
updateDocumentTitle(pageMeta)
</script>

<template>
	<header class="sticky top-0 z-10 flex items-center justify-between bg-white px-5 py-2.5">
		<PageBreadcrumbs
			class="h-7"
			:items="[
				{ label: 'Notebooks', route: { path: '/notebook' } },
				{
					label: notebook.doc.title || notebook.doc.name,
					route: { path: `/notebook/${notebook.doc.name}` },
				},
				{ label: page.doc.title },
			]"
		/>
	</header>
	<div class="flex flex-1 overflow-hidden bg-white px-6 py-2">
		<div
			v-if="page.doc.name"
			class="h-full w-full overflow-y-scroll bg-white pb-96 pt-16 text-base"
		>
			<div class="w-full px-[6rem] lg:mx-auto lg:max-w-[65rem]">
				<div class="flex items-center">
					<ContentEditable
						class="flex-1 text-[36px] font-bold"
						v-model="page.doc.title"
						placeholder="Untitled Analysis"
					></ContentEditable>
					<Dropdown
						:button="{ icon: 'more-horizontal', variant: 'ghost' }"
						:options="[
							{
								label: 'Clear',
								icon: 'x-square',
								onClick: () => (page.doc.content = {}),
							},
							{
								label: 'Delete',
								icon: 'trash',
								onClick: () => (show_delete_dialog = true),
							},
						]"
					/>
				</div>
				<TipTap class="my-6" v-model:content="page.doc.content" />
			</div>
		</div>
	</div>

	<Dialog
		:options="{
			title: 'Delete Page',
			icon: { name: 'trash', variant: 'solid', theme: 'red' },
		}"
		v-model="show_delete_dialog"
		:dismissable="true"
	>
		<template #body-content>
			<p class="text-base text-gray-600">Are you sure you want to delete this page?</p>
		</template>
		<template #actions>
			<Button variant="solid" theme="red" :loading="page.delete.loading" @click="deletePage">
				Yes
			</Button>
		</template>
	</Dialog>
</template>
