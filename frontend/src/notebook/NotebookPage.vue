<script setup lang="jsx">
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import useNotebook from '@/notebook/useNotebook'
import useNotebookPage from '@/notebook/useNotebookPage'
import ContentEditable from '@/notebook/ContentEditable.vue'
import TipTap from './tiptap/TipTap.vue'

const props = defineProps({
	notebook: String,
	page: String,
})
const page = useNotebookPage(props.page)
const notebook = useNotebook(props.notebook)
</script>

<template>
	<div class="h-full w-full bg-white px-6 py-4">
		<Breadcrumbs
			:items="[
				{
					label: 'Notebooks',
					href: '/notebook',
				},
				{
					label: notebook.doc.title,
					href: `/notebook/${page.doc.notebook}`,
				},
				{
					label: page.doc.title,
					href: `/notebook/${page.doc.notebook}/${page.doc.name}`,
				},
			]"
		>
		</Breadcrumbs>
		<div
			v-if="page.doc.name"
			class="h-full w-full overflow-y-scroll bg-white pb-96 pt-16 text-base"
		>
			<div class="mx-auto w-[50rem]">
				<ContentEditable
					class="focusable text-[36px] font-bold"
					v-model="page.doc.title"
					placeholder="Page Title"
				></ContentEditable>
				<TipTap class="my-6" v-model:content="page.doc.content" />
			</div>
		</div>
	</div>
</template>