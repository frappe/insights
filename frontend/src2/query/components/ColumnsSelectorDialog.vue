<script setup lang="ts">
import { SearchIcon } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import DraggableList from '../../components/DraggableList.vue'
import { QueryResultColumn, SelectArgs } from '../../types/query.types'
import { Query } from '../query'
import DataTypeIcon from './DataTypeIcon.vue'

const props = defineProps<{ columns?: SelectArgs }>()
const emit = defineEmits({
	select: (args: SelectArgs) => true,
})
const showDialog = defineModel()

const query = inject('query') as Query
const selectedColumns = ref<QueryResultColumn[]>([...query.result.columns])

const columnOptions = ref<ColumnOption[]>([])
query.getColumnsForSelection().then((cols: ColumnOption[]) => {
	columnOptions.value = cols
})

const columns = ref<HTMLElement | null>(null)
function addColumn(column: ColumnOption) {
	if (!column?.value) return
	if (!selectedColumns.value.find((c) => c.name === column.value)) {
		selectedColumns.value.push({
			name: column.value,
			type: column.data_type,
		})
		setTimeout(() => {
			columns.value?.scrollTo({
				top: columns.value.scrollHeight,
				behavior: 'smooth',
			})
		}, 100)
	}
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
			<div class="-mb-7 flex max-h-[22rem] flex-col gap-4 p-0.5 text-base">
				<Autocomplete
					:options="
						columnOptions.filter(
							(c) => !selectedColumns.find((sc) => sc.name === c.value)
						)
					"
					placeholder="Add column"
					@update:modelValue="addColumn"
				>
					<template #prefix>
						<SearchIcon class="h-4 w-4 text-gray-500" stroke-width="1.5" />
					</template>
				</Autocomplete>

				<div ref="columns" class="relative overflow-y-scroll">
					<DraggableList
						v-model:items="selectedColumns"
						:item-key="'name'"
						group="columns"
					>
						<template #item-content="{ item }">
							<div class="flex items-center gap-1.5">
								<DataTypeIcon :columnType="item.type" />
								<span>{{ item.name }}</span>
							</div>
						</template>
					</DraggableList>

					<p class="sticky bottom-0 bg-white pt-1.5 text-sm text-gray-500">
						{{ selectedColumns.length }} columns selected
					</p>
				</div>
			</div>
		</template>
	</Dialog>
</template>
