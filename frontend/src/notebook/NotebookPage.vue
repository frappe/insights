<script setup lang="jsx">
import ContentEditable from '@/components/ContentEditable.vue'
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import useNotebook from '@/notebook/useNotebook'
import useNotebookPage from '@/notebook/useNotebookPage'
import { updateDocumentTitle } from '@/utils'
import { computed, provide } from 'vue'
import NotebookPageDropdown from './NotebookPageDropdown.vue'
import TipTap from './tiptap/TipTap.vue'

const props = defineProps({ notebook: String, name: String })
const page = useNotebookPage(props.name)
const notebook = useNotebook(props.notebook)
provide('page', page)

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
			class="h-full w-full overflow-y-auto bg-white pb-96 pt-16 text-base scrollbar-hide"
		>
			<div class="w-full px-[6rem] lg:mx-auto lg:max-w-[62rem]">
				<div class="flex items-center">
					<ContentEditable
						class="flex-1 text-[36px] font-bold"
						v-model="page.doc.title"
						placeholder="Untitled Analysis"
					></ContentEditable>
					<NotebookPageDropdown />
				</div>
				<TipTap class="my-6" v-model:content="page.doc.content" />
			</div>
		</div>
	</div>
</template>
