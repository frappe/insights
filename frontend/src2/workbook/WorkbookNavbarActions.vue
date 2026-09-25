<script setup lang="ts">
import { GitFork, PackagePlus, Share2 } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import router from '../router'
import session from '../session'
import { __ } from '../translation'
import { canExportToApp } from './export_to_app'
import type { Workbook } from './workbook'
import { workbookKey } from './workbook_key'
import WorkbookExportToAppDialog from './WorkbookExportToAppDialog.vue'
import WorkbookLineageDialog from './WorkbookLineageDialog.vue'
import WorkbookShareDialog from './WorkbookShareDialog.vue'

const workbook = inject(workbookKey) as Workbook

const showShareDialog = ref(false)
const showLineageDialog = ref(false)
const showExportDialog = ref(false)

const canExport = computed(() => canExportToApp(workbook.doc))

function afterMarked(name: string) {
	// The workbook and its queries, charts and dashboards now have new names, so
	// every resource in this tab points at a document that is gone. Reload the
	// workbook instead of patching each resource. Duplicate does the same.
	window.location.href = router.resolve({
		name: 'Workbook',
		params: { workbook_name: name },
	}).href
}
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
			align="end"
			:options="[
				{
					label: __('View Lineage'),
					icon: GitFork,
					onClick: () => (showLineageDialog = true),
				},
				!workbook.doc.read_only || workbook.doc.can_copy
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
				canExport && !workbook.islocal
					? {
							label: __('Export to app…'),
							icon: PackagePlus,
							onClick: () => (showExportDialog = true),
					  }
					: null,
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
	<WorkbookExportToAppDialog
		v-if="showExportDialog"
		v-model="showExportDialog"
		@marked="afterMarked"
	/>
</template>
