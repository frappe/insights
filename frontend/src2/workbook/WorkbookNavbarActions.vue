<script setup lang="ts">
import { inject, ref } from 'vue'
import { Workbook, workbookKey } from './workbook'
import WorkbookShareDialog from './WorkbookShareDialog.vue'

const workbook = inject(workbookKey) as Workbook

const showShareDialog = ref(false)
</script>

<template>
	<div class="flex gap-2">
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
