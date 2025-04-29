<script setup lang="ts">
import { ChevronDown, SearchIcon } from 'lucide-vue-next'
import { computed, inject, ref, watchEffect } from 'vue'
import DraggableList from '../../components/DraggableList.vue'
import { ColumnOption, QueryResultColumn, SelectArgs } from '../../types/query.types'
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
function addColumns(options: ColumnOption[]) {
	selectedColumns.value = options.map((o) => ({
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
			query.result.columns.map((c) => c.name).join()
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
		v-model="showDialog"
		:options="{
			size: 'sm',
			title: 'Select Columns',
			actions: [
				{
					label: 'Confirm',
					variant: 'solid',
					disabled: confirmDisabled,
					onClick: confirmSelection,
				},
				{
					label: 'Cancel',
					onClick: () => (showDialog = false),
				},
			],
		}"
	>
		<template #body-content>
			<div class="-mb-7 flex h-[22rem] flex-col p-0.5 text-base">
				<Autocomplete
					class="flex-shrink-0"
					:multiple="true"
					:options="columnOptions"
					placeholder="Add column"
					:modelValue="selectedColumns.map((c) => c.name)"
					@update:modelValue="addColumns"
				>
					<template #target="{ togglePopover }">
						<Button class="w-full !justify-start" @click="togglePopover">
							<template #prefix>
								<SearchIcon class="h-4 w-4 text-gray-500" stroke-width="1.5" />
							</template>
							<span class="flex-1 text-gray-500">Add column</span>
							<template #suffix>
								<ChevronDown
									class="ml-auto h-4 w-4 text-gray-500"
									stroke-width="1.5"
								/>
							</template>
						</Button>
					</template>
				</Autocomplete>

				<div ref="columns" class="relative mt-4 flex-1 overflow-y-scroll">
					<DraggableList
						v-model:items="selectedColumns"
						:item-key="'name'"
						group="columns"
						empty-text="No columns selected"
					>
						<template #item-content="{ item }">
							<div class="flex items-center gap-1.5">
								<DataTypeIcon :columnType="item.type" />
								<span class="truncate">{{ item.name }}</span>
							</div>
						</template>
					</DraggableList>
				</div>

				<p class="flex-shrink-0 bg-white pt-1.5 text-sm text-gray-500">
					{{ selectedColumns.length }} columns selected
				</p>
			</div>
		</template>
	</Dialog>
</template>
