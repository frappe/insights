<script setup lang="ts">
import { Share2 } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import session from '../session'
import { Workbook, workbookKey } from './workbook'
import WorkbookShareDialog from './WorkbookShareDialog.vue'

const workbook = inject(workbookKey) as Workbook

const showShareDialog = ref(false)

const restoreSnapshotActions = computed(() => {
	if (!workbook) return []
	return (
		workbook.doc.snapshots?.map((snapshot) => ({
			label: `Restore: ${snapshot.title || snapshot.name}`,
			icon: 'rotate-ccw',
			onClick: () => workbook.restoreSnapshot(snapshot.name),
		})) || []
	)
})
</script>

<template>
	<div v-if="workbook" class="flex gap-2">
		<Button
			v-if="workbook.canShare && !workbook.isdirty && !workbook.islocal"
			variant="outline"
			@click="showShareDialog = true"
		>
			<template #prefix>
				<Share2 class="h-4 w-4 text-gray-700" stroke-width="1.5" />
			</template>
			Share
		</Button>
		<Dropdown
			:button="{ icon: 'more-horizontal', variant: 'outline' }"
			:options="[
				!workbook.doc.read_only
					? {
							label: 'Duplicate',
							icon: 'copy',
							onClick: () => workbook.duplicate(),
					  }
					: null,
				!workbook.doc.read_only
					? {
							label: 'Save Snapshot',
							icon: 'copy',
							onClick: () => workbook.snapshot(),
					  }
					: null,
				...restoreSnapshotActions,
				{
					label: 'Copy JSON',
					icon: 'copy',
					onClick: () => workbook.copy(),
				},
				!workbook.islocal
					? {
							label: 'Delete',
							icon: 'trash-2',
							onClick: () => workbook.delete(),
					  }
					: null,
				session.user.has_desk_access
					? {
							label: 'Open in Desk',
							icon: 'external-link',
							onClick: () => workbook.openInDesk(),
					  }
					: null,
			]"
		/>
	</div>

	<WorkbookShareDialog v-if="workbook.canShare && showShareDialog" v-model="showShareDialog" />
</template>
