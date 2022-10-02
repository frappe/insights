<script setup>
import { inject, ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const dashboard = inject('dashboard')

const router = useRouter()
const showDeleteDialog = ref(false)
const deletingDashboard = computed(() => dashboard.delete.loading)
const deleteDashboard = () => {
	dashboard.delete.submit().then(() => {
		showDeleteDialog.value = false
		router.push('/dashboard')
	})
}

const refreshVisualizations = async () => {
	dashboard.refreshing = true
	// hack: update the visualizations
	await dashboard.refreshVisualizations.submit()
	// then reload the dashboard doc
	// to re-render the visualizations with new data
	dashboard.doc.visualizations = []
	await dashboard.reload()
	dashboard.refreshing = false
}

defineEmits(['addChart', 'commitLayout'])
</script>

<template>
	<div class="flex flex-1 items-center justify-between">
		<h1 v-if="dashboard.doc" class="text-3xl font-medium text-gray-900">
			{{ dashboard.doc.title }}
		</h1>
		<div class="flex items-start space-x-2">
			<Button
				v-if="!dashboard.editingLayout"
				appearance="white"
				iconLeft="refresh-ccw"
				@click="refreshVisualizations"
			>
				Refresh
			</Button>
			<Button
				v-if="!dashboard.editingLayout"
				appearance="white"
				iconLeft="edit"
				@click="() => (dashboard.editingLayout = true)"
			>
				Edit
			</Button>
			<Button
				v-if="dashboard.editingLayout"
				appearance="white"
				icon="plus"
				@click="$emit('addChart')"
			/>
			<Button
				v-if="!dashboard.editingLayout"
				appearance="white"
				class="!text-red-600"
				iconLeft="trash-2"
				@click="() => (showDeleteDialog = true)"
			>
				Delete
			</Button>
			<Button
				v-if="dashboard.editingLayout"
				appearance="danger"
				icon="x"
				@click="dashboard.editingLayout = false"
			/>
			<Button
				v-if="dashboard.editingLayout"
				appearance="primary"
				icon="check"
				@click="$emit('commitLayout')"
			/>
		</div>
	</div>

	<Dialog
		:options="{ title: 'Delete Query', icon: { name: 'trash', appearance: 'danger' } }"
		v-model="showDeleteDialog"
		:dismissable="true"
	>
		<template #body-content>
			<p class="text-base text-gray-600">Are you sure you want to delete this dashboard?</p>
		</template>
		<template #actions>
			<Button appearance="danger" @click="deleteDashboard" :loading="deletingDashboard">
				Yes
			</Button>
		</template>
	</Dialog>
</template>
