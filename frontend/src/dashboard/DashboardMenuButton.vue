<script setup>
import useTemplateStore from '@/stores/templateStore'
import BrowseTemplatesDialog from '@/templates/BrowseTemplatesDialog.vue'
import { inject, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

const dashboard = inject('dashboard')
const showDeleteDialog = ref(false)
const router = useRouter()
async function handleDelete() {
	await dashboard.deleteDashboard()
	showDeleteDialog.value = false
	router.push({ name: 'Dashboards' })
}

const showCreateTemplateDialog = ref(false)
const showTemplatesDialog = ref(false)
const template = reactive({
	title: dashboard.doc.title,
	description: '',
})

const templateStore = useTemplateStore()
function handleCreateTemplate() {
	templateStore
		.createTemplate({
			title: template.title,
			description: template.description,
			dashboard_name: dashboard.doc.name,
		})
		.then(() => {
			showCreateTemplateDialog.value = false
			showTemplatesDialog.value = true
		})
}
</script>

<template>
	<Dropdown
		v-if="dashboard.doc"
		placement="left"
		:button="{ icon: 'more-vertical', variant: 'outline' }"
		:options="[
			{
				label: 'Publish as Template',
				variant: 'outline',
				icon: 'download',
				onClick: () => (showCreateTemplateDialog = true),
			},
			{
				label: 'Delete',
				variant: 'outline',
				theme: 'red',
				icon: 'trash-2',
				onClick: () => (showDeleteDialog = true),
			},
		]"
	/>

	<Dialog
		v-model="showDeleteDialog"
		:dismissable="true"
		:options="{
			title: 'Delete Dashboard',
			message: 'Are you sure you want to delete this dashboard?',
			icon: { name: 'trash', variant: 'solid', theme: 'red' },
			actions: [
				{ label: 'Cancel', variant: 'outline', onClick: () => (showDeleteDialog = false) },
				{ label: 'Yes', variant: 'solid', theme: 'red', onClick: handleDelete },
			],
		}"
	>
	</Dialog>

	<Dialog
		v-model="showCreateTemplateDialog"
		:dismissable="true"
		:options="{
			title: 'Create a Template',
			actions: [
				{
					label: 'Upload to Marketplace',
					variant: 'solid',
					iconLeft: 'upload',
					loading: dashboard.creatingTemplate,
					onClick: handleCreateTemplate,
				},
			],
		}"
	>
		<template #body-content>
			<div class="mb-4 -mt-4">
				<p class="text-base text-gray-500">
					You can share your dashboard with other users by exporting it as a template on
					the marketplace.
				</p>
			</div>

			<div class="mb-2 flex flex-col space-y-4 text-base">
				<Input type="text" label="Template Title" v-model="template.title" class="w-full" />
				<Input
					type="textarea"
					label="Template Description"
					v-model="template.description"
					class="h-20 w-full"
				/>
			</div>
		</template>
	</Dialog>

	<BrowseTemplatesDialog
		v-model:show="showTemplatesDialog"
		activeTab="My Templates"
		title="Marketplace"
	/>
</template>
