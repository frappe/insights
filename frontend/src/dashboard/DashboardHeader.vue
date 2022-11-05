<script setup>
import { inject, ref } from 'vue'
import { useRouter } from 'vue-router'
import EditablePageTitle from '@/components/EditablePageTitle.vue'

const dashboard = inject('dashboard')

const router = useRouter()
const showDeleteDialog = ref(false)

defineEmits(['addChart', 'commitLayout'])

const $notify = inject('$notify')
function updateTitle(title) {
	if (!title || title === dashboard.doc.title) return
	dashboard.setValue.submit({ title }).then(() => {
		$notify({
			title: 'Dashboard title updated',
			appearance: 'success',
		})
		dashboard.doc.title = title
	})
}
</script>

<template>
	<div class="flex flex-1 items-center justify-between">
		<EditablePageTitle
			v-if="dashboard.doc"
			:title="dashboard.doc.title"
			@update="updateTitle"
		/>
		<div class="flex items-start space-x-2">
			<Button
				v-if="!dashboard.editingLayout"
				appearance="white"
				iconLeft="refresh-ccw"
				@click="dashboard.refreshItems"
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
		:options="{
			title: 'Delete Query',
			icon: { name: 'trash', appearance: 'danger' },
		}"
		v-model="showDeleteDialog"
		:dismissable="true"
	>
		<template #body-content>
			<p class="text-base text-gray-600">Are you sure you want to delete this dashboard?</p>
		</template>
		<template #actions>
			<Button
				appearance="danger"
				@click="
					dashboard.deleteDashboard().then(() => {
						showDeleteDialog = false
						router.push('/dashboard')
					})
				"
				:loading="dashboard.deletingDashboard"
			>
				Yes
			</Button>
		</template>
	</Dialog>
</template>
