<script setup lang="ts">
import { Plus, SortAscIcon, SortDescIcon, X } from 'lucide-vue-next'
import { computed } from 'vue'
import DraggableList from '../../components/DraggableList.vue'
import { column } from '../../query/helpers'
import { ColumnOption, OrderByArgs } from '../../types/query.types'

const props = defineProps<{ columnOptions: ColumnOption[] }>()
const sortColumns = defineModel<OrderByArgs[]>({
	default: () => [],
})

const listItems = computed(() => {
	return sortColumns.value.map((order) => ({
		...order,
		value: order.column.column_name,
	}))
})

function addSortColumn(column_name: string) {
	const existing = sortColumns.value.find((s) => s.column.column_name === column_name)
	if (existing) return
	sortColumns.value.push({
		column: column(column_name),
		direction: 'asc',
	})
}
function removeSortColumn(index: number) {
	sortColumns.value.splice(index, 1)
}
function updateSortColumn(index: number, column_name: string) {
	const existing = sortColumns.value[index]
	sortColumns.value.splice(index, 1, {
		column: column(column_name),
		direction: existing?.direction || 'asc',
	})
}
function toggleSortDirection(index: number) {
	const existing = sortColumns.value[index]
	if (!existing) return
	sortColumns.value.splice(index, 1, {
		...existing,
		direction: existing.direction === 'asc' ? 'desc' : 'asc',
	})
}
function moveSortColumn(from: number, to: number) {
	if (!sortColumns.value) return
	const toMove = sortColumns.value.splice(from, 1)
	sortColumns.value.splice(to, 0, ...toMove)
}
</script>

<template>
	<div class="flex flex-col gap-2">
		<DraggableList
			group="sortColumns"
			:show-empty-state="false"
			:items="listItems"
			@sort="moveSortColumn"
		>
			<template #item="{ item, index }">
				<div class="flex rounded">
					<Button
						class="flex-shrink-0 rounded-r-none border-r"
						@click="toggleSortDirection(index)"
					>
						<template #icon>
							<SortAscIcon
								v-if="item.direction == 'asc'"
								class="h-4 w-4 text-ink-gray-6"
								stroke-width="1.5"
							/>
							<SortDescIcon
								v-else
								class="h-4 w-4 text-ink-gray-6"
								stroke-width="1.5"
							/>
						</template>
					</Button>
					<div class="flex-1 overflow-hidden">
						<Combobox
							:options="props.columnOptions"
							:modelValue="item.value"
							@update:modelValue="updateSortColumn(index, $event)"
						>
							<template #trigger>
								<Button
									class="w-full !justify-start rounded-none [&>span]:truncate"
								>
									{{ item.column.column_name }}
								</Button>
							</template>
						</Combobox>
					</div>
					<Button
						class="flex-shrink-0 rounded-l-none border-l"
						@click="removeSortColumn(index)"
					>
						<template #icon>
							<X class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
						</template>
					</Button>
				</div>
			</template>
		</DraggableList>

		<!-- add sort button -->
		<Combobox :options="props.columnOptions" @update:modelValue="addSortColumn($event)">
			<template #trigger>
				<Button class="w-full">
					<template #prefix>
						<Plus class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
					</template>
					Add Sort
				</Button>
			</template>
		</Combobox>
	</div>
</template>
