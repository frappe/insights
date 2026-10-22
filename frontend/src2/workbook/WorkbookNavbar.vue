<script setup lang="ts">
import { inject } from 'vue'
import ContentEditable from '../components/ContentEditable.vue'
import { workbookKey } from './workbook_key'
import WorkbookNavbarActions from './WorkbookNavbarActions.vue'
import { Avatar } from 'frappe-ui'
import { LockIcon } from 'lucide-vue-next'

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
				<div class="relative flex min-w-0 items-center">
					<template v-if="workbook.doc.shipped_by">
						<Tooltip
							:text="
								__(
									'Shipped with {0}. Duplicate it to make changes.',
									workbook.doc.shipped_by,
								)
							"
						>
							<span
								tabindex="0"
								class="flex shrink-0 items-center gap-1.5 rounded-4 px-0.5 text-base text-ink-gray-5 focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
							>
								<Avatar
									class="shrink-0"
									size="xs"
									shape="square"
									:label="workbook.doc.shipped_by"
									:image="workbook.doc.shipped_by_logo ?? undefined"
								/>
								{{ workbook.doc.shipped_by }}
							</span>
						</Tooltip>
						<span class="mx-1 text-base text-ink-gray-4" aria-hidden="true">/</span>
					</template>
					<Tooltip
						v-else-if="workbook.doc.read_only"
						:text="__('You have read-only access to this workbook')"
					>
						<LockIcon
							tabindex="0"
							role="img"
							:aria-label="__('You have read-only access to this workbook')"
							class="absolute -left-6 size-4 rounded-4 text-ink-gray-5 focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
							stroke-width="1.5"
						/>
					</Tooltip>
					<ContentEditable
						class="font-medium !text-ink-gray-7"
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
