<script setup>
import { computed, ref } from 'vue'

const emit = defineEmits(['row-select'])
const props = defineProps({
	title: { type: String },
	actions: { type: Array },
	filters: { type: Array },
	columns: { type: Array },
	data: { type: Array },
	rowClick: { type: Function },
})
const searchTerm = ref('')
const filteredData = computed(() => {
	if (searchTerm.value === '') {
		return props.data
	}
	return props.data
		.filter((row) => {
			return Object.values(row).some((value) => {
				return String(value).toLowerCase().includes(searchTerm.value.toLowerCase())
			})
		})
		.slice(0, 100)
})
const selectedIndex = ref([])
function selectAll() {
	if (selectedIndex.value.length === props.data.length) {
		selectedIndex.value.splice(0, selectedIndex.value.length)
	} else {
		selectedIndex.value.splice(
			0,
			selectedIndex.value.length,
			...props.data.map((_, index) => index)
		)
	}
}
function isSelected(row) {
	return selectedIndex.value.includes(props.data.indexOf(row))
}
function toggleSelected(row) {
	const index = props.data.indexOf(row)
	if (isSelected(row)) {
		selectedIndex.value.splice(selectedIndex.value.indexOf(index), 1)
	} else {
		selectedIndex.value.push(index)
	}
}
</script>
<template>
	<div class="flex h-full w-full flex-col overflow-hidden">
		<!-- Title -->
		<div class="flex h-12 flex-shrink-0 items-center justify-between">
			<slot name="title">
				<div class="text-3xl font-medium text-gray-900">{{ title }}</div>
			</slot>
			<div class="flex space-x-4">
				<Button
					v-for="action in actions"
					:key="action.label"
					class="shadow-sm"
					:appearance="action.appearance"
					:iconLeft="action.iconLeft"
					@click="action.handler"
				>
					{{ action.label }}
				</Button>
			</div>
		</div>

		<!-- Filter Bar -->
		<div class="flex flex-1 flex-col overflow-hidden">
			<div class="my-4 flex justify-between">
				<div class="flex space-x-4">
					<div class="flex items-center rounded-md bg-gray-100 px-3">
						<FeatherIcon name="search" class="h-4 w-4 text-gray-500" />
						<input
							ref="searchInput"
							v-model="searchTerm"
							class="flex w-64 items-center bg-gray-100 px-2.5 py-1.5 focus:outline-none"
							placeholder="Search..."
						/>
					</div>
				</div>
				<!-- Enable after grid feature -->
				<!-- <div class="flex items-center space-x-1 rounded-md bg-gray-100 p-1">
					<div class="cursor-pointer rounded-md px-2 py-1 transition-all">
						<FeatherIcon name="grid" class="h-4 w-4" />
					</div>
					<div class="cursor-pointer rounded-md bg-white px-2 py-1 shadow transition-all">
						<FeatherIcon name="list" class="h-4 w-4" />
					</div>
				</div> -->
			</div>

			<!-- Data -->
			<div
				v-if="props.data.length > 0"
				class="relative flex flex-1 flex-col overflow-y-scroll text-lg"
			>
				<table class="w-full flex-1">
					<thead>
						<tr class="sticky top-0 z-10 border-b bg-white text-gray-400">
							<th scope="col" width="1%" class="pr-3">
								<Input
									type="checkbox"
									class="rounded-md border-gray-300"
									@click="selectAll"
								/>
							</th>
							<th
								v-for="(column, idx) in columns"
								:key="column.label"
								class="whitespace-nowrap py-4 text-left font-normal"
								:class="column.class || ''"
								scope="col"
								:width="column.width || idx === 0 ? '20%' : '10%'"
							>
								<component :is="column.headerComponent || 'div'">
									{{ column.label }}
								</component>
							</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="row in filteredData"
							:key="row[columns[0].key]"
							class="border-b text-gray-500"
							:class="props.rowClick ? 'cursor-pointer hover:bg-gray-50' : ''"
							@click="props.rowClick && props.rowClick(row)"
						>
							<td width="1%" class="pr-3">
								<Input
									type="checkbox"
									class="rounded-md border-gray-300"
									:checked="isSelected(row)"
									@click="toggleSelected(row)"
								/>
							</td>
							<td
								v-for="(column, idx) in columns"
								:key="column.label"
								class="py-4"
								:width="column.width || idx === 0 ? '20%' : '10%'"
							>
								<component
									:is="column.cellComponent || 'div'"
									:row="row"
									class="whitespace-nowrap"
									:class="[idx === 0 ? 'font-medium text-gray-700' : '']"
								>
									{{ row[column.key] }}
								</component>
							</td>
						</tr>
						<tr height="99%"></tr>
					</tbody>
				</table>

				<div
					class="sticky bottom-0 right-0 flex w-full border-t bg-white py-3 text-lg text-gray-500"
				>
					<p class="ml-auto">
						Showing {{ filteredData.length }} of {{ props.data.length }} results
					</p>
				</div>
			</div>

			<div v-else class="flex-1 overflow-hidden">
				<slot name="empty-state">
					<div
						class="flex h-full w-full flex-col items-center justify-center text-lg text-gray-400/50"
					>
						<FeatherIcon name="folder" class="h-12 w-12" />
						<p class="mt-4">No data to display</p>
					</div>
				</slot>
			</div>
		</div>
	</div>
</template>
