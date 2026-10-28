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
				<ContentEditable
					class="font-medium !text-ink-gray-7 !gap-1.5"
					:modelValue="workbook.doc.title"
					placeholder="Untitled Workbook"
					@returned="workbook.doc.title = $event"
					@blur="workbook.doc.title = $event"
				>
					<!-- in the title's box, so the logo or lock and the title are centred as
					     one, 6px apart, as frappe-ui's PageHeaderMobileTitle does. Raised 1px to
					     centre on the capitals, which sit above the middle of the line box -->
					<template v-if="workbook.doc.shipped_by" #prefix>
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
								role="img"
								:aria-label="
									__(
										'Shipped with {0}. Duplicate it to make changes.',
										workbook.doc.shipped_by,
									)
								"
								class="flex shrink-0 -translate-y-px rounded-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
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
					<template v-else-if="workbook.doc.read_only" #prefix>
						<Tooltip :text="__('You have read-only access to this workbook')">
							<LockIcon
								tabindex="0"
								role="img"
								:aria-label="__('You have read-only access to this workbook')"
								class="size-4 shrink-0 -translate-y-px rounded-4 text-ink-gray-5 focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
								stroke-width="1.5"
							/>
						</Tooltip>
					</template>
				</ContentEditable>
			</div>
			<div class="absolute right-0">
				<WorkbookNavbarActions />
			</div>
		</div>
	</div>
</template>
