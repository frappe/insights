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
							<!-- outside the title's box, as the read-only lock is, so the title
							     stays centred. The box's padding is most of the gap, and 4px
							     keep its focus border off the logo -->
							<span
								tabindex="0"
								role="img"
								:aria-label="
									__(
										'Shipped with {0}. Duplicate it to make changes.',
										workbook.doc.shipped_by,
									)
								"
								class="absolute -left-5 flex rounded-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
							>
								<Avatar
									size="xs"
									shape="square"
									:label="workbook.doc.shipped_by"
									:image="workbook.doc.shipped_by_logo ?? undefined"
								/>
							</span>
						</Tooltip>
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
