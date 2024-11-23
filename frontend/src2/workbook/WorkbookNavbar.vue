<script setup lang="ts">
import { Badge } from 'frappe-ui'
import { inject } from 'vue'
import ContentEditable from '../components/ContentEditable.vue'
import { workbookKey } from './workbook'
import WorkbookNavbarActions from './WorkbookNavbarActions.vue'

const workbook = inject(workbookKey)!
</script>

<template>
	<div
		class="sticky top-0 z-10 flex h-11 w-full flex-shrink-0 items-center gap-3 bg-white px-3 shadow-sm"
	>
		<div class="relative flex flex-1 items-center">
			<div class="absolute left-0">
				<slot name="left">
					<router-link :to="{ path: '/workbook' }">
						<img src="../assets/insights-logo-new.svg" alt="logo" class="h-7 rounded" />
					</router-link>
				</slot>
			</div>
			<div class="flex flex-1 items-center justify-center">
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
			</div>
			<div class="absolute right-0">
				<WorkbookNavbarActions />
			</div>
		</div>
	</div>
</template>
