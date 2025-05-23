<script setup lang="tsx">
import { Avatar, Breadcrumbs, ListView } from 'frappe-ui'
import { Building2, Eye, Lock, PlusIcon, SearchIcon, Shield } from 'lucide-vue-next'
import { computed, ref, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import { wheneverChanges } from '../helpers'
import { WorkbookListItem } from '../types/workbook.types'
import useUserStore from '../users/users'
import useWorkbook, { newWorkbookName } from './workbook'
import useWorkbooks from './workbooks'
import { useMagicKeys, whenever } from '@vueuse/core'

const router = useRouter()
const workbookStore = useWorkbooks()
const workbooks = computed(() => workbookStore.workbooks)

const searchQuery = ref('')
wheneverChanges(searchQuery, () => workbookStore.getWorkbooks(searchQuery.value), {
	debounce: 300,
	immediate: true,
})

const creatingWorkbook = ref(false)
function openNewWorkbook() {
	creatingWorkbook.value = true
	const workbook = useWorkbook(newWorkbookName())
	workbook
		.insert()
		.then((doc) => {
			router.push(`/workbook/${doc.name}`)
		})
		.finally(() => {
			creatingWorkbook.value = false
		})
}

const userStore = useUserStore()
const listOptions = ref({
	columns: [
		{
			label: 'Title',
			key: 'title',
			width: 4,
		},
		{
			label: 'Access',
			key: 'shared_with',
			width: 2,
			getLabel: (props: any) => {
				const workbook = props.row as WorkbookListItem
				if (workbook.shared_with_organization) {
					return 'Everyone'
				}
				if (workbook.shared_with.length === 0) {
					return 'Private'
				}
				return workbook.shared_with.length > 1
					? `${workbook.shared_with.length} people`
					: userStore.getName(workbook.shared_with[0])
			},
			prefix: (props: any) => {
				const workbook = props.row as WorkbookListItem
				if (workbook.shared_with_organization) {
					return <Building2 class="h-3.5 w-3.5 text-blue-500" />
				}
				if (workbook.shared_with.length === 0) {
					return <Lock class="h-3.5 w-3.5 text-orange-500" />
				}
				return <Shield class="h-3.5 w-3.5 text-green-500" />
			},
		},
		{
			label: 'Views',
			key: 'views',
			width: 1.5,
			getLabel: (props: any) => {},
			prefix: (props: any) => {
				const workbook = props.row as WorkbookListItem
				return (
					<div class="flex gap-1">
						<Eye class="h-3.5 w-3.5 text-gray-600" stroke-width="1.5" />
						<span class="font-mono text-sm text-gray-700">{workbook.views}</span>
					</div>
				)
			},
		},
		{
			label: 'Owner',
			key: 'owner',
			width: 2,
			getLabel(props: any) {
				const workbook = props.row as WorkbookListItem
				const user = userStore.getUser(workbook.owner)
				return user?.full_name || workbook.owner
			},
			prefix: (props: any) => {
				const workbook = props.row as WorkbookListItem
				const user = userStore.getUser(workbook.owner)
				return <Avatar size="md" label={workbook.owner} image={user?.user_image} />
			},
		},
		{ label: 'Modified', key: 'modified_from_now', width: 2 },
	],
	rows: workbooks,
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
				loading: creatingWorkbook,
			},
		},
	},
})

const keys = useMagicKeys()
const cmdV = keys['Meta+V']
whenever(cmdV, () => {
	if (!navigator.clipboard) {
		return
	}
	navigator.clipboard.readText().then((text) => {
		try {
			const json = JSON.parse(text)
			if (json.type === 'Workbook') {
				workbookStore.importWorkbook(json)
			}
		} catch (e) {}
	})
})

watchEffect(() => {
	document.title = 'Workbooks | Insights'
})
</script>

<template>
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs :items="[{ label: 'Workbooks', route: '/workbook' }]" />
		<div class="flex items-center gap-2">
			<Button
				label="New Workbook"
				variant="solid"
				@click="openNewWorkbook"
				:loading="creatingWorkbook"
			>
				<template #prefix>
					<PlusIcon class="w-4" />
				</template>
			</Button>
		</div>
	</header>

	<div class="mb-4 flex h-full flex-col gap-3 overflow-auto px-5 py-3">
		<div class="flex gap-2 overflow-visible py-1">
			<FormControl
				placeholder="Search by Title"
				v-model="searchQuery"
				:debounce="300"
				autocomplete="off"
			>
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" />
				</template>
			</FormControl>
		</div>
		<ListView class="h-full" v-bind="listOptions"> </ListView>
	</div>
</template>
