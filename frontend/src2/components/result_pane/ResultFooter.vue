<script setup lang="ts">
import { Button } from 'frappe-ui'
import { Download } from 'lucide-vue-next'
import type { PaginationState } from '../../composables/usePagination'
import { __ } from '../../translation'
import DataTableFooter from '../DataTableFooter.vue'

// The pane's bottom band: the result's status on the left, the pager and the
// one act that takes the whole of it out on the right.
const props = defineProps<{
	/** absent while there is nothing to page through — a failed or empty run */
	pagination?: PaginationState
	onExport?: () => void
}>()
</script>

<template>
	<DataTableFooter
		:pagination="props.pagination"
		@prev="props.pagination?.prev()"
		@next="props.pagination?.next()"
	>
		<template #left>
			<slot name="left" />
		</template>

		<template v-if="props.onExport" #actions>
			<Button variant="ghost" :tooltip="__('Export')" @click="props.onExport">
				<template #icon>
					<Download class="size-3.5 text-ink-gray-6" stroke-width="1.5" />
				</template>
			</Button>
		</template>
	</DataTableFooter>
</template>
