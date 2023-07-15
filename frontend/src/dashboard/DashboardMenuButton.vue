<script setup>
import { inject, ref } from 'vue'
import { useRouter } from 'vue-router'

const dashboard = inject('dashboard')
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
		:button="{ icon: 'more-vertical', variant: 'white' }"
		:options="[
			{
				label: 'Delete',
				icon: 'trash-2',
				handler: () => (showDeleteDialog = true),
			},
		]"
	/>

	<Dialog
		:options="{
			title: 'Delete Dashboard',
			icon: { name: 'trash', variant: 'danger' },
		}"
		v-model="showDeleteDialog"
		:dismissable="true"
	>
		<template #body-content>
			<p class="text-base text-gray-600">Are you sure you want to delete this dashboard?</p>
		</template>
		<template #actions>
			<Button variant="white" @click="showDeleteDialog = false">Cancel</Button>
			<Button variant="danger" @click="handleDelete" :loading="dashboard.deleting">
				Yes
			</Button>
		</template>
	</Dialog>
</template>
