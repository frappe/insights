<script setup lang="ts">
import { Badge } from 'frappe-ui'
import { inject } from 'vue'
import ContentEditable from '../components/ContentEditable.vue'
import { workbookKey } from './workbook_key'
import WorkbookNavbarActions from './WorkbookNavbarActions.vue'
import { PencilIcon, PencilOff, PenOff, ShieldAlert } from 'lucide-vue-next'

const workbook = inject(workbookKey)!
</script>

<template>
	<div
		class="flex h-11 w-full flex-shrink-0 items-center gap-3 bg-surface-base px-3 border-b border-outline-gray-2"
	>
		<div class="relative flex flex-1 items-center">
			<div class="absolute left-0">
				<slot name="left">
					<router-link :to="{ path: '/workbook' }">
						<img
							src="../assets/insights-logo-new.svg"
							alt="logo"
							class="h-7 rounded-4"
						/>
					</router-link>
				</slot>
			</div>
			<div class="flex flex-1 items-center justify-center">
				<div class="relative flex items-center gap-3">
					<Tooltip
						v-if="workbook.doc.read_only"
						text="You have read-only access to this workbook"
					>
						<ShieldAlert
							class="absolute -left-6 h-4 w-4 cursor-pointer text-ink-orange-7"
							stroke-width="1.5"
						/>
					</Tooltip>
					<ContentEditable
						class="rounded-1 font-medium !text-ink-gray-7 focus:ring-2 focus:ring-outline-gray-6 focus:ring-offset-4"
						:modelValue="workbook.doc.title"
						placeholder="Untitled Workbook"
						@returned="workbook.doc.title = $event"
						@blur="workbook.doc.title = $event"
					></ContentEditable>
				</div>
			</div>
			<div class="absolute right-0">
				<WorkbookNavbarActions />
			</div>
		</div>
	</div>
</template>
