<script setup lang="ts">
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import { ListView } from 'frappe-ui'
import { PlusIcon, SearchIcon } from 'lucide-vue-next'
import { computed, ref, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { getUniqueId } from '../helpers'
import useWorkbooks, { WorkbookListItem } from './workbooks'

const router = useRouter()
const workbookStore = useWorkbooks()
const searchQuery = ref('')
const filteredWorkbooks = computed(() => {
	if (!searchQuery.value) {
		return workbookStore.workbooks
	}
	return workbookStore.workbooks.filter((workbook) =>
		workbook.title.toLowerCase().includes(searchQuery.value.toLowerCase())
	)
})

function openNewWorkbook() {
	const unique_id = getUniqueId()
	const name = `new-workbook-${unique_id}`
	router.push(`/workbook/${name}`)
}

watchEffect(() => {
	document.title = 'Workbooks | Insights'
})
</script>

<template>
	<header class="mb-2 flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<PageBreadcrumbs class="h-7" :items="[{ label: 'Workbooks' }]" />
		<div class="flex items-center gap-2">
			<Button label="New Notebook" variant="solid" @click="openNewWorkbook">
				<template #prefix>
					<PlusIcon class="w-4" />
				</template>
			</Button>
		</div>
	</header>

	<div class="mb-4 flex h-full flex-col gap-2 overflow-auto px-4">
		<div class="flex gap-2 overflow-visible py-1">
			<FormControl placeholder="Search by Title" v-model="searchQuery" :debounce="300">
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" />
				</template>
			</FormControl>
		</div>
		<ListView
			class="h-full"
			:columns="[
				{ label: 'Title', key: 'title' },
				{ label: 'Owner', key: 'owner' },
				{ label: 'Created', key: 'created_from_now' },
				{ label: 'Modified', key: 'modified_from_now' },
			]"
			:rows="filteredWorkbooks"
			:row-key="'name'"
			:options="{
				showTooltip: false,
				getRowRoute: (workbook: WorkbookListItem) => ({
					name: 'Workbook',
					params: { name: workbook.name },
				}),
				emptyState: {
					title: 'No workbooks.',
					description: 'No workbooks to display.',
					button: {
						label: 'New Workbook',
						variant: 'solid',
						onClick: openNewWorkbook,
					},
				},
			}"
		>
		</ListView>
	</div>
</template>
