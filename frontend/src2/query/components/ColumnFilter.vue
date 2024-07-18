<script setup lang="ts">
import { ChevronRight, ListFilter } from 'lucide-vue-next'
import { FilterOperator, FilterValue, QueryResultColumn } from '../../types/query.types'
import ColumnFilterBody from './ColumnFilterBody.vue'

const emit = defineEmits({
	filter: (operator: FilterOperator, value: FilterValue) => true,
})
const props = defineProps<{
	column: QueryResultColumn
	valuesProvider: (search: string) => Promise<string[]>
	placement?: string
}>()
</script>

<template>
	<Popover :placement="props.placement || 'right-start'">
		<template #target="{ togglePopover, isOpen }">
			<slot name="target" :togglePopover="togglePopover" :isOpen="isOpen">
				<Button
					variant="ghost"
					@click="togglePopover"
					class="w-full !justify-start"
					:class="{ ' !bg-gray-100': isOpen }"
				>
					<template #icon>
						<div class="flex h-7 w-full items-center gap-2 pl-2 pr-1.5 text-base">
							<ListFilter class="h-4 w-4 flex-shrink-0" stroke-width="1.5" />
							<div class="flex flex-1 items-center justify-between">
								<span class="truncate">Filter</span>
								<ChevronRight class="h-4 w-4" stroke-width="1.5" />
							</div>
						</div>
					</template>
				</Button>
			</slot>
		</template>
		<template #body-main="{ togglePopover, isOpen }">
			<ColumnFilterBody
				v-if="isOpen"
				:column="props.column"
				:valuesProvider="props.valuesProvider"
				@filter="(op, val) => emit('filter', op, val)"
				@close="togglePopover"
			/>
		</template>
	</Popover>
</template>
