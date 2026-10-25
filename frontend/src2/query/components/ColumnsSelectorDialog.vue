<script setup lang="ts">
import { SearchIcon } from 'lucide-vue-next'
import { computed, inject, ref, watchEffect } from 'vue'
import DraggableList from '../../components/DraggableList.vue'
import { ColumnOption, QueryResultColumn, SelectArgs } from '../../types/query.types'
import { __ } from '../../translation'
import { Query } from '../query'
import DataTypeIcon from './DataTypeIcon.vue'

const props = defineProps<{ columns?: SelectArgs }>()
const emit = defineEmits({
	select: (args: SelectArgs) => true,
})
const showDialog = defineModel()

const query = inject('query') as Query
const selectedColumns = ref<QueryResultColumn[]>([])
watchEffect(() => {
	selectedColumns.value = [...query.result.columns]
})

const columnOptions = ref<ColumnOption[]>([])
query.getColumnsForSelection().then((cols) => (columnOptions.value = cols))

const columns = ref<HTMLElement | null>(null)
function addColumns(values: string[]) {
	selectedColumns.value = values
		.map((v) => columnOptions.value.find((o) => o.value === v))
		.filter((o): o is ColumnOption => Boolean(o))
		.map((o) => ({
			name: o.value,
			type: o.data_type,
		}))

	setTimeout(() => {
		columns.value?.scrollTo({
			top: columns.value.scrollHeight,
			behavior: 'smooth',
		})
	}, 100)
}

const confirmDisabled = computed(
	() =>
		selectedColumns.value.length === 0 ||
		selectedColumns.value.map((c) => c.name).join() ===
			query.result.columns.map((c) => c.name).join(),
)
function confirmSelection() {
	emit('select', {
		column_names: selectedColumns.value
			.map((c) => c.name)
			.filter((c) => c)
			.filter((c, i, a) => a.indexOf(c) === i),
	})
	showDialog.value = false
}
</script>

<template>
	<Dialog
		v-model:open="showDialog"
		size="sm"
		:title="__('Select Columns')"
		:actions="[
			{
				label: __('Confirm'),
				variant: 'solid',
				disabled: confirmDisabled,
				onClick: confirmSelection,
			},
			{
				label: __('Cancel'),
				onClick: () => (showDialog = false),
			},
		]"
	>
		<template #default>
			<div class="-mb-7 flex h-[22rem] flex-col p-0.5 text-base">
				<MultiSelect
					class="w-full flex-shrink-0"
					:options="columnOptions"
					:placeholder="__('Add column')"
					:modelValue="selectedColumns.map((c) => c.name)"
					@update:modelValue="addColumns"
				>
					<template #prefix>
						<SearchIcon class="h-4 w-4 text-ink-gray-4" stroke-width="1.5" />
					</template>
					<template #summary>
						<span class="text-ink-gray-4">{{ __('Add column') }}</span>
					</template>
				</MultiSelect>

				<div ref="columns" class="relative mt-4 flex-1 overflow-y-scroll">
					<DraggableList
						v-model:items="selectedColumns"
						:item-key="'name'"
						group="columns"
						:empty-text="__('No columns selected')"
					>
						<template #item-content="{ item }">
							<div class="flex items-center gap-1.5">
								<DataTypeIcon :columnType="item.type" />
								<span class="truncate">{{ item.name }}</span>
							</div>
						</template>
					</DraggableList>
				</div>

				<p class="flex-shrink-0 bg-surface-base pt-1.5 text-sm text-ink-gray-4">
					{{ __('{0} columns selected', String(selectedColumns.length)) }}
				</p>
			</div>
		</template>
	</Dialog>
</template>
