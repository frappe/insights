<script setup>
import { computed, ref } from 'vue'
import { ellipsis } from '@/utils'
import PageTitle from './PageTitle.vue'

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
		return props.data.slice(0, 100)
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
		<PageTitle v-if="title" :title="title" :actions="actions">
			<slot name="title-items"></slot>
		</PageTitle>

		<div class="flex flex-1 flex-col overflow-hidden">
			<!-- Filter Bar -->
			<div class="my-2 flex justify-between">
				<div class="flex space-x-4">
					<Input
						ref="searchInput"
						v-model="searchTerm"
						iconLeft="search"
						placeholder="Search..."
					/>
				</div>
				<!-- Enable after grid feature -->
				<!-- <div class="flex items-center space-x-1 rounded bg-gray-100 p-1">
					<div class="cursor-pointer rounded px-2 py-1 transition-all">
						<FeatherIcon name="grid" class="h-4 w-4" />
					</div>
					<div class="cursor-pointer rounded bg-white px-2 py-1 shadow transition-all">
						<FeatherIcon name="list" class="h-4 w-4" />
					</div>
				</div> -->
			</div>

			<!-- Data -->
			<ul
				v-if="props.data.length > 0"
				class="relative flex flex-1 flex-col overflow-y-scroll text-lg"
			>
				<li
					class="sticky top-0 z-10 flex items-center gap-4 border-b bg-white text-gray-500"
				>
					<div>
						<Input
							type="checkbox"
							class="rounded border-gray-300"
							@click.prevent.stop="selectAll"
						/>
					</div>
					<div
						v-for="(column, idx) in columns"
						:key="column.label"
						class="py-4 text-left font-normal"
						:class="[column.class, idx === 0 ? 'w-[30%]' : 'flex-1']"
						scope="col"
					>
						<component :is="column.headerComponent || 'span'">
							{{ column.label }}
						</component>
					</div>
				</li>
				<li
					v-for="row in filteredData"
					:key="row[columns[0].key]"
					class="flex items-center gap-4 border-b text-gray-600"
					:class="props.rowClick ? 'cursor-pointer hover:bg-gray-50' : ''"
					@click="props.rowClick && props.rowClick(row)"
				>
					<div>
						<Input
							type="checkbox"
							class="rounded border-gray-300"
							:checked="isSelected(row)"
							@click.stop="toggleSelected(row)"
						/>
					</div>
					<div
						v-for="(column, idx) in columns"
						:key="column.label"
						class="overflow-hidden text-ellipsis whitespace-nowrap py-4"
						:class="[idx === 0 ? 'w-[30%]' : 'flex-1']"
					>
						<component
							:is="column.cellComponent || 'span'"
							:row="row"
							:class="[idx === 0 ? 'font-medium text-gray-700' : '']"
						>
							{{ ellipsis(row[column.key], 80) }}
						</component>
					</div>
				</li>

				<li
					class="sticky bottom-0 right-0 flex w-full flex-1 flex-shrink-0 items-end bg-white"
				>
					<div class="mb-3 flex w-full justify-end border-t py-3 text-lg text-gray-600">
						<p>Showing {{ filteredData.length }} of {{ props.data.length }} results</p>
					</div>
				</li>
			</ul>

			<div v-else class="flex-1 overflow-hidden">
				<slot name="empty-state">
					<div
						class="flex h-full w-full flex-col items-center justify-center text-lg text-gray-500/50"
					>
						<FeatherIcon name="folder" class="h-12 w-12" />
						<p class="mt-4">No data to display</p>
					</div>
				</slot>
			</div>
		</div>
	</div>
</template>
