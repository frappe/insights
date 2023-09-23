<script setup>
import { List } from 'frappe-ui'
import { computed, ref } from 'vue'

const props = defineProps({
	columns: { type: Array },
	rows: { type: Array },
})

const searchQuery = ref('')
const filteredList = computed(() => {
	if (!props.rows) return []
	if (!searchQuery.value) return props.rows.slice(0, 100)
	return props.rows
		.filter((row) => {
			return Object.values(row).some((value) => {
				return String(value).toLowerCase().includes(searchQuery.value.toLowerCase())
			})
		})
		.slice(0, 100)
})
</script>

<template>
	<div class="flex h-full w-full flex-col overflow-hidden">
		<div class="flex px-6 py-0.5">
			<div class="flex space-x-2">
				<Input
					placeholder="Search"
					icon-left="search"
					:value="searchQuery"
					:debounce="500"
					@input="searchQuery = $event"
				/>
				<slot name="actions" />
			</div>
		</div>
		<div class="flex flex-1 overflow-hidden bg-white px-4 py-2">
			<List :columns="props.columns" :rows="filteredList">
				<template #list-row="{ row }">
					<slot name="list-row" :row="row" />
				</template>
			</List>

			<div
				v-if="props.rows?.length == 0"
				class="flex h-full w-full flex-col items-center justify-center"
			>
				<slot name="emptyState">
					<div class="text-xl font-medium">No data.</div>
					<div class="mt-1 text-base text-gray-600">No data to display.</div>
				</slot>
			</div>
		</div>
	</div>
</template>
