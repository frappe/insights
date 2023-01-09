<script setup>
import { inject, ref } from 'vue'
import { useRouter } from 'vue-router'
import EditablePageTitle from '@/components/EditablePageTitle.vue'
import { Dropdown } from 'frappe-ui'
import ShareDialog from '@/components/ShareDialog.vue'

const dashboard = inject('dashboard')

const router = useRouter()
const showDeleteDialog = ref(false)
const showShareDialog = ref(false)

defineEmits(['addChart', 'saveLayout', 'autoLayout'])

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
		<div class="flex items-center space-x-2">
			<EditablePageTitle
				v-if="dashboard.doc"
				:title="dashboard.doc.title"
				@update="updateTitle"
			/>

			<Button
				v-if="dashboard.isOwner"
				icon="share-2"
				appearance="minimal"
				@click="() => (showShareDialog = true)"
			/>

			<Dropdown
				v-if="dashboard.doc"
				placement="left"
				:button="{ icon: 'more-horizontal', appearance: 'minimal' }"
				:options="[
					{
						label: 'Delete',
						icon: 'trash-2',
						handler: () => {},
					},
				]"
			/>
		</div>
		<div class="flex items-start space-x-2">
			<Button
				appearance="white"
				v-if="!dashboard.editingLayout"
				iconLeft="refresh-ccw"
				@click="dashboard.refreshItems"
			>
				Refresh
			</Button>
			<Button
				appearance="white"
				v-if="!dashboard.editingLayout"
				iconLeft="edit"
				@click="() => (dashboard.editingLayout = true)"
			>
				Edit
			</Button>
			<Button
				appearance="white"
				v-if="dashboard.editingLayout"
				iconLeft="plus"
				@click="$emit('addChart')"
			>
				Add
			</Button>
			<Button
				appearance="white"
				v-if="dashboard.editingLayout"
				iconLeft="grid"
				@click="$emit('autoLayout')"
			>
				Auto Layout
			</Button>
			<Button
				appearance="white"
				v-if="!dashboard.editingLayout"
				iconLeft="trash-2"
				@click="() => (showDeleteDialog = true)"
			>
				Delete
			</Button>
			<Button
				appearance="white"
				v-if="dashboard.editingLayout"
				iconLeft="x"
				@click="dashboard.editingLayout = false"
			>
				Cancel
			</Button>
			<Button
				appearance="white"
				v-if="dashboard.editingLayout"
				iconLeft="check"
				@click="$emit('saveLayout')"
			>
				Save
			</Button>
		</div>
	</div>

	<Dialog
		:options="{
			title: 'Delete Dashboard',
			icon: { name: 'trash', appearance: 'danger' },
		}"
		v-model="showDeleteDialog"
		:dismissable="true"
	>
		<template #body-content>
			<p class="text-base text-gray-600">Are you sure you want to delete this dashboard?</p>
		</template>
		<template #actions>
			<Button appearance="white" @click="showDeleteDialog = false">Cancel</Button>
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

	<ShareDialog
		v-if="dashboard.doc"
		v-model:show="showShareDialog"
		:resource-type="dashboard.doc.doctype"
		:resource-name="dashboard.doc.name"
	/>
</template>
