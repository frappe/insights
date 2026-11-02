<script setup lang="ts">
import { Button } from 'frappe-ui'
import { ChevronRight, Layers, Rows3 } from 'lucide-vue-next'
import { __ } from '../../translation'

// What a segment click offers first: its rows, or a breakdown. `DrillMenu` lists
// them where the reader clicked, and the upgrade wizard pictures them.
const props = defineProps<{
	/** Whether the reader may read the rows behind the segment. */
	canRows?: boolean
	/** Whether the segment can still be broken down by another column. */
	canBreakDown: boolean
}>()

const emit = defineEmits<{
	rows: []
	breakdown: []
}>()

// A row here is a ghost Button: an ItemListRow renders without its own utilities
// inside the drill menu.
const rowClass = 'w-full !justify-start'
</script>

<template>
	<div class="flex flex-col gap-0.5">
		<Button
			v-if="props.canRows !== false"
			variant="ghost"
			:class="rowClass"
			@click="emit('rows')"
		>
			<template #prefix>
				<Rows3 class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
			</template>
			<span class="truncate">{{ __('View rows') }}</span>
		</Button>
		<!-- A segment that pins every dimension the query has left cannot be
		     split any further, and the rows are the only way on. -->
		<Button
			v-if="props.canBreakDown"
			variant="ghost"
			:class="rowClass"
			@click="emit('breakdown')"
		>
			<template #prefix>
				<Layers class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
			</template>
			<span class="truncate">{{ __('Break down by') }}</span>
			<template #suffix>
				<ChevronRight class="h-4 w-4 text-ink-gray-5" stroke-width="1.5" />
			</template>
		</Button>
		<p
			v-if="props.canRows === false && !props.canBreakDown"
			class="px-2 py-1.5 text-base text-ink-gray-5"
		>
			{{ __('Nothing to drill into here') }}
		</p>
	</div>
</template>
