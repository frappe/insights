<script setup lang="ts">
import { ListFilter } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import { copy } from '../helpers'
import { COLUMN_TYPES } from '../helpers/constants'
import ColumnFilterBody from '../query/components/ColumnFilterBody.vue'
import { WorkbookDashboardFilter } from '../types/workbook.types'
import { Dashboard } from './dashboard'

const dashboard = inject<Dashboard>('dashboard')!
const props = defineProps<{ item: WorkbookDashboardFilter }>()

const editedFilter = ref(copy(props.item))
const editDisabled = computed(() => {
	return (
		!editedFilter.value.filter_name ||
		!editedFilter.value.data_type ||
		(editedFilter.value.filter_name === props.item.filter_name &&
			editedFilter.value.data_type === props.item.data_type)
	)
})
</script>

<template>
	<div class="h-8 [&>div:first-child]:h-full">
		<Popover class="h-full">
			<template #target="{ togglePopover, isOpen }">
				<Button
					variant="outline"
					:label="props.item.filter_name"
					class="flex h-full w-full !justify-start shadow-sm"
					@click="togglePopover"
				>
					<template #prefix>
						<ListFilter class="h-4 w-4 flex-shrink-0" stroke-width="1.5" />
					</template>
				</Button>
			</template>
			<template #body-main="{ togglePopover, isOpen }">
				<ColumnFilterBody
					v-if="isOpen"
					:column="{
						name: props.item.filter_name,
						type: props.item.data_type,
					}"
					:valuesProvider="() => []"
					@close="togglePopover"
				/>
			</template>
		</Popover>
	</div>

	<Dialog
		v-if="dashboard.isEditingItem(props.item)"
		:modelValue="dashboard.isEditingItem(props.item)"
		@update:modelValue="!$event ? (dashboard.editingItemIndex = null) : true"
		:options="{
			title: 'Edit Filter',
			actions: [
				{
					label: 'Save',
					variant: 'solid',
					disabled: editDisabled,
					onClick: () => {
						props.item.filter_name = editedFilter.filter_name
						props.item.data_type = editedFilter.data_type
						dashboard.editingItemIndex = null
					},
				},
				{
					label: 'Cancel',
					onClick: () => (dashboard.editingItemIndex = null),
				},
			],
		}"
	>
		<template #body-content>
			<div class="flex flex-col gap-4">
				<div class="flex gap-4">
					<FormControl
						class="flex-1 flex-shrink-0"
						label="Label"
						v-model="editedFilter.filter_name"
						autocomplete="off"
					/>
					<FormControl
						class="flex-1 flex-shrink-0"
						v-model="editedFilter.data_type"
						label="Type"
						type="select"
						:options="COLUMN_TYPES"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>
