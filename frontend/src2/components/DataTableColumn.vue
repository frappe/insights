<script setup lang="ts">
import { ArrowDownWideNarrow, ArrowUpDown, ArrowUpNarrowWide, XIcon } from 'lucide-vue-next'
import { h, ref, watchEffect } from 'vue'
import { SortDirection } from '../types/query.types'
import ContentEditable from './ContentEditable.vue'

const props = defineProps<{
	label: string
	sortOrder?: SortDirection
	onSortChange?: (direction: SortDirection) => void
	onRename?: (new_name: string) => void
}>()

const _label = ref(props.label)
watchEffect(() => (_label.value = props.label))

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
	<div class="flex w-full items-center gap-0.5">
		<slot name="prefix" />
		<ContentEditable
			v-model="_label"
			placeholder="Column"
			class="flex h-6 items-center whitespace-nowrap rounded-sm px-0.5 text-sm font-medium first:ml-2 focus:ring-1 focus:ring-gray-700 focus:ring-offset-1"
			:disabled="!props.onRename"
			@returned="props.onRename?.(_label)"
			@blur="props.onRename?.(_label)"
		/>
		<Dropdown v-if="props.onSortChange" :options="sortOptions">
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
		<slot name="suffix" />
	</div>
</template>
