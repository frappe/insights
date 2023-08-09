<script setup>
import { inject, ref } from 'vue'
import { useRouter } from 'vue-router'

const dashboard = inject('dashboard')
const showExportDialog = ref(false)
const showDeleteDialog = ref(false)
const router = useRouter()
async function handleDelete() {
	await dashboard.deleteDashboard()
	showDeleteDialog.value = false
	router.push({ name: 'Dashboards' })
}
</script>

<template>
	<Dropdown
		v-if="dashboard.doc"
		placement="left"
		:button="{ icon: 'more-vertical', variant: 'outline' }"
		:options="[
			{
				label: 'Export',
				variant: 'outline',
				icon: 'download',
				onClick: () => (showExportDialog = true),
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
		v-model="showExportDialog"
		:dismissable="true"
		:options="{
			title: 'Export Dashboard',
			message:
				'Exporting a dashboard will create a JSON file that can be imported into another dashboard.',
			icon: { name: 'download', variant: 'solid' },
			actions: [
				{ label: 'Cancel', variant: 'outline', onClick: () => (showExportDialog = false) },
				{
					label: 'Export',
					variant: 'solid',
					onClick: () =>
						dashboard.exportDashboard().then(() => (showExportDialog = false)),
				},
			],
		}"
	>
	</Dialog>
</template>
