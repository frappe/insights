<script setup lang="ts">
import { inject, ref } from 'vue'
import { Workbook, workbookKey } from './workbook'
import WorkbookShareDialog from './WorkbookShareDialog.vue'
import { PanelRightClose, PanelRightOpen } from 'lucide-vue-next'

const workbook = inject(workbookKey) as Workbook

const showShareDialog = ref(false)
</script>

<template>
	<div v-if="workbook" class="flex gap-2">
		<Button
			v-if="workbook.canShare && !workbook.isdirty && !workbook.islocal"
			variant="outline"
			@click="showShareDialog = true"
		>
			Share
		</Button>
		<Button
			v-show="!workbook.islocal && workbook.isdirty"
			variant="outline"
			@click="workbook.discard()"
		>
			Discard
		</Button>
		<Button
			v-show="workbook.islocal || workbook.isdirty"
			variant="solid"
			:loading="workbook.saving"
			@click="workbook.save()"
		>
			Save
		</Button>
		<Dropdown
			:button="{ icon: 'more-horizontal', variant: 'outline' }"
			:options="[
				{
					label: workbook.showSidebar ? 'Hide Sidebar' : 'Show Sidebar',
					icon: workbook.showSidebar ? PanelRightOpen : PanelRightClose,
					onClick: () => (workbook.showSidebar = !workbook.showSidebar),
				},
				!workbook.islocal
					? {
							label: 'Delete',
							icon: 'trash-2',
							onClick: () => workbook.delete(),
					  }
					: null,
			]"
		/>
	</div>

	<WorkbookShareDialog v-if="workbook.canShare && showShareDialog" v-model="showShareDialog" />
</template>
