<script setup lang="ts">
import { GitFork, Share2 } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import session from '../session'
import { __ } from '../translation'
import { Workbook, workbookKey } from './workbook'
import WorkbookLineageDialog from './WorkbookLineageDialog.vue'
import WorkbookShareDialog from './WorkbookShareDialog.vue'

const workbook = inject(workbookKey) as Workbook

const showShareDialog = ref(false)
const showLineageDialog = ref(false)
</script>

<template>
	<div v-if="workbook" class="flex gap-2">
		<Button
			v-if="workbook.canShare && !workbook.isdirty && !workbook.islocal"
			variant="outline"
			@click="showShareDialog = true"
		>
			<template #prefix>
				<Share2 class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
			</template>
			Share
		</Button>
		<Dropdown
			:button="{ icon: 'lucide-more-horizontal', variant: 'outline' }"
			placement="right"
			:options="[
				{
					label: __('View Lineage'),
					icon: GitFork,
					onClick: () => (showLineageDialog = true),
				},
				!workbook.doc.read_only
					? {
							label: __('Duplicate'),
							icon: 'lucide-copy',
							onClick: () => workbook.duplicate(),
					  }
					: null,
				{
					label: __('Copy JSON'),
					icon: 'lucide-copy',
					onClick: () => workbook.copy(),
				},
				!workbook.islocal
					? {
							label: __('Delete'),
							icon: 'lucide-trash-2',
							onClick: () => workbook.delete(),
					  }
					: null,
				session.user.has_desk_access
					? {
							label: __('Open in Desk'),
							icon: 'lucide-external-link',
							onClick: () => workbook.openInDesk(),
					  }
					: null,
			]"
		/>
	</div>

	<WorkbookShareDialog v-if="workbook.canShare && showShareDialog" v-model="showShareDialog" />
	<WorkbookLineageDialog v-if="showLineageDialog" v-model="showLineageDialog" />
</template>
