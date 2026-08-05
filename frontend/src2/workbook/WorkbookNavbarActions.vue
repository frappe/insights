<script setup lang="ts">
import { GitFork, PackagePlus, Share2 } from 'lucide-vue-next'
import { computed, inject, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import router from '../router'
import session from '../session'
import { __ } from '../translation'
import { canExportToApp, loadExportTargets } from './export_targets'
import type { Workbook } from './workbook'
import { workbookKey } from './workbook_key'
import WorkbookExportToAppDialog from './WorkbookExportToAppDialog.vue'
import WorkbookLineageDialog from './WorkbookLineageDialog.vue'
import WorkbookShareDialog from './WorkbookShareDialog.vue'

const workbook = inject(workbookKey) as Workbook
const route = useRoute()

const showShareDialog = ref(false)
const showLineageDialog = ref(false)
const showExportDialog = ref(false)

const activeDashboard = computed(() => {
	if (route.name !== 'WorkbookDashboard') return
	const name = route.params.dashboard_name as string
	return workbook.doc.dashboards.find((d) => d.name === name)
})

// only a dashboard can be exported, so a bench that never opens one never asks
watch(activeDashboard, (dashboard) => dashboard && loadExportTargets(), { immediate: true })

function afterExport() {
	// the dashboard, its charts and their queries now belong to the bundle's
	// workbook, so every cached resource in this tab is stale and the tab the
	// user is on is gone: reload the workbook rather than patch the pieces
	window.location.href = router.resolve({
		name: 'Workbook',
		params: { workbook_name: workbook.name },
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
				activeDashboard && canExportToApp
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
		v-if="showExportDialog && activeDashboard"
		v-model="showExportDialog"
		:dashboard="activeDashboard.name"
		:title="activeDashboard.title"
		@exported="afterExport"
	/>
</template>
