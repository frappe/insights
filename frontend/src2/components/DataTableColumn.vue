<script setup lang="ts">
import { ArrowDownWideNarrow, ArrowUpDown, ArrowUpNarrowWide, XIcon } from 'lucide-vue-next'
import { h } from 'vue'
import { QueryResultColumn } from '../types/query.types'

const props = defineProps<{
	label: string
	column: QueryResultColumn
	sortOrder?: 'asc' | 'desc'
	onSortChange?: (sort_order: 'asc' | 'desc' | '') => void
}>()

const sortOptions = [
	{
		label: 'Sort Ascending',
		icon: h(ArrowUpNarrowWide, { class: 'h-4 w-4 text-gray-700', strokeWidth: 1.5 }),
		onClick: () => props.onSortChange?.('asc'),
	},
	{
		label: 'Sort Descending',
		icon: h(ArrowDownWideNarrow, { class: 'h-4 w-4 text-gray-700', strokeWidth: 1.5 }),
		onClick: () => props.onSortChange?.('desc'),
	},
	{
		label: 'Remove Sort',
		icon: h(XIcon, { class: 'h-4 w-4 text-gray-700', strokeWidth: 1.5 }),
		onClick: () => props.onSortChange?.(''),
	},
]
</script>

<template>
	<div class="flex items-center gap-3 pl-3">
		<span class="truncate">
			{{ props.label }}
		</span>

		<div class="flex">
			<!-- Sort -->
			<Dropdown :options="sortOptions">
				<Button variant="ghost" class="rounded-none">
					<template #icon>
						<component
							:is="
								!props.sortOrder
									? ArrowUpDown
									: props.sortOrder === 'asc'
									? ArrowUpNarrowWide
									: ArrowDownWideNarrow
							"
							class="h-3.5 w-3.5 text-gray-700"
							stroke-width="1.5"
						/>
					</template>
				</Button>
			</Dropdown>
		</div>
	</div>
</template>
