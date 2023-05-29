<script setup lang="jsx">
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import ContentEditable from '@/notebook/ContentEditable.vue'
import useNotebook from '@/notebook/useNotebook'
import useNotebookPage from '@/notebook/useNotebookPage'
import TipTap from './tiptap/TipTap.vue'
import { provide, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { updateDocumentTitle } from '@/utils'

const props = defineProps({
	notebook: String,
	page: String,
})
const page = useNotebookPage(props.page)
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
			<div class="w-full px-[6rem] lg:mx-auto lg:max-w-[60rem]">
				<div class="flex items-center">
					<ContentEditable
						class="focusable flex-1 text-[36px] font-bold"
						v-model="page.doc.title"
						placeholder="Page Title"
					></ContentEditable>
					<Dropdown
						:button="{ icon: 'more-horizontal', appearance: 'minimal' }"
						:options="[
							{
								label: 'Delete',
								icon: 'trash',
								handler: () => (show_delete_dialog = true),
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
			icon: { name: 'trash', appearance: 'danger' },
		}"
		v-model="show_delete_dialog"
		:dismissable="true"
	>
		<template #body-content>
			<p class="text-base text-gray-600">Are you sure you want to delete this page?</p>
		</template>
		<template #actions>
			<Button appearance="danger" :loading="page.delete.loading" @click="deletePage">
				Yes
			</Button>
		</template>
	</Dialog>
</template>
