<script setup>
import { inject, ref } from 'vue'
import { useRouter } from 'vue-router'

const page = inject('page')
const show_delete_dialog = ref(false)

const router = useRouter()
function deletePage() {
	const notebook_name = page.doc.notebook
	page.delete().then(() => {
		router.push(`/notebook/${notebook_name}`)
	})
}
</script>

<template>
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

	<Dialog
		:options="{
			title: 'Delete Page',
			icon: { name: 'trash', variant: 'solid', theme: 'red' },
			actions: [
				{
					label: 'Delete',
					variant: 'solid',
					theme: 'red',
					loading: page.delete.loading,
					onClick: deletePage,
				},
			],
		}"
		v-model="show_delete_dialog"
		:dismissable="true"
	>
		<template #body-content>
			<p class="text-base text-gray-600">Are you sure you want to delete this page?</p>
		</template>
	</Dialog>
</template>
