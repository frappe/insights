<script setup lang="ts">
import { Check, PanelRightClose, PanelRightOpen, Share2, Undo2 } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import { Workbook, workbookKey } from './workbook'
import WorkbookShareDialog from './WorkbookShareDialog.vue'

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
			<template #prefix>
				<Share2 class="h-4 w-4 text-gray-700" stroke-width="1.5" />
			</template>
			Share
		</Button>
		<Button
			v-show="!workbook.islocal && workbook.isdirty"
			variant="outline"
			@click="workbook.discard()"
		>
			<template #prefix>
				<Undo2 class="h-4 w-4 text-gray-700" stroke-width="1.5" />
			</template>
			Discard
		</Button>
		<Button
			v-show="workbook.islocal || workbook.isdirty"
			variant="solid"
			:loading="workbook.saving"
			@click="workbook.save()"
		>
			<template #prefix>
				<Check class="h-4 w-4 text-gray-100" stroke-width="1.5" />
			</template>
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
