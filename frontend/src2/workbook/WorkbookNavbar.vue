<script setup lang="ts">
import { Badge } from 'frappe-ui'
import { inject } from 'vue'
import ContentEditable from '../components/ContentEditable.vue'
import Navbar from '../components/Navbar.vue'
import { workbookKey } from './workbook'
import WorkbookNavbarActions from './WorkbookNavbarActions.vue'

const workbook = inject(workbookKey)!
</script>

<template>
	<Navbar>
		<template #center>
			<div class="relative flex gap-3">
				<ContentEditable
					class="rounded-sm font-medium !text-gray-800 focus:ring-2 focus:ring-gray-700 focus:ring-offset-4"
					v-model="workbook.doc.title"
					placeholder="Untitled Workbook"
				></ContentEditable>
				<Badge
					v-if="workbook.islocal || workbook.isdirty"
					class="absolute -right-[4.5rem]"
					size="sm"
					theme="orange"
				>
					Unsaved
				</Badge>
			</div>
		</template>
		<template #right>
			<WorkbookNavbarActions />
		</template>
	</Navbar>
</template>
