<script setup lang="tsx">
import { Avatar, Breadcrumbs, ListView } from 'frappe-ui'
import { PlusIcon, SearchIcon } from 'lucide-vue-next'
import { computed, ref, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { getUniqueId } from '../helpers'
import { WorkbookListItem } from '../types/workbook.types'
import useUserStore from '../users/users'
import useWorkbooks from './workbooks'

const router = useRouter()
const workbookStore = useWorkbooks()
workbookStore.getWorkbooks()

const searchQuery = ref('')
const filteredWorkbooks = computed(() => {
	if (!searchQuery.value) {
		return workbookStore.workbooks
	}
	return workbookStore.workbooks.filter((workbook) =>
		workbook.title.toLowerCase().includes(searchQuery.value.toLowerCase())
	)
})

const userStore = useUserStore()
const listOptions = ref({
	columns: [
		{ label: 'Title', key: 'title' },
		{
			label: 'Owner',
			key: 'owner',
			getLabel(props: any) {
				const workbook = props.row as WorkbookListItem
				const user = userStore.getUser(workbook.owner)
				return user?.full_name
			},
			prefix: (props: any) => {
				const workbook = props.row as WorkbookListItem
				const user = userStore.getUser(workbook.owner)
				return <Avatar size="md" label={workbook.owner} image={user?.user_image} />
			},
		},
		{ label: 'Created', key: 'created_from_now' },
		{ label: 'Modified', key: 'modified_from_now' },
	],
	rows: filteredWorkbooks,
	rowKey: 'name',
	options: {
		showTooltip: false,
		getRowRoute: (workbook: WorkbookListItem) => ({
			path: `/workbook/${workbook.name}`,
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
	},
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
		<Breadcrumbs :items="[{ label: 'Workbooks', route: '/workbook' }]" />
		<div class="flex items-center gap-2">
			<Button label="New Workbook" variant="solid" @click="openNewWorkbook">
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
		<ListView class="h-full" v-bind="listOptions"> </ListView>
	</div>
</template>
