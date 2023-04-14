<template>
	<BasePage>
		<template #header>
			<div v-if="dataSource.doc" class="flex flex-1 items-center space-x-4">
				<div class="flex items-start space-x-4">
					<h1 class="text-3xl font-medium text-gray-900">
						{{ dataSource.doc.title }}
					</h1>
					<div class="flex h-8 items-center">
						<Badge color="green" class="h-fit">Active</Badge>
					</div>
				</div>
				<div class="space-x-2">
					<Dropdown
						placement="left"
						:button="{ icon: 'more-horizontal', appearance: 'minimal' }"
						:options="[
							dataSource.doc.allow_imports
								? {
										label: 'Import CSV',
										icon: 'upload',
										handler: () => (showImportDialog = true),
								  }
								: null,
							{
								label: 'Sync Tables',
								icon: 'refresh-cw',
								handler: syncTables,
							},
							{
								label: 'Delete',
								icon: 'trash',
								handler: () => dataSource.delete(),
							},
						]"
					/>
				</div>
			</div>
		</template>
		<template #main>
			<div v-if="dataSource.tables" class="flex flex-1 flex-col overflow-hidden pt-2">
				<div class="mb-4 flex flex-shrink-0 space-x-4">
					<Input type="text" placeholder="Label" v-model="labelFilter" />
					<Input
						type="select"
						placeholder="Status"
						v-model="statusFilter"
						:options="['Disabled', 'Enabled', 'All']"
					/>
				</div>
				<div class="flex flex-1 flex-col overflow-hidden rounded-md border">
					<!-- List Header -->
					<div
						class="flex flex-shrink-0 items-center justify-between border-b px-4 py-3 text-sm text-gray-500"
					>
						<p class="mr-4">
							<Input type="checkbox" class="rounded-md border-gray-300" />
						</p>
						<p class="flex-1">Table</p>
						<p class="flex-1">Status</p>
					</div>
					<ul
						v-if="tables.length > 0"
						role="list"
						class="flex flex-1 flex-col divide-y divide-gray-200 overflow-y-scroll"
					>
						<li v-for="table in tables" :key="table.table">
							<router-link
								:to="{
									name: 'DataSourceTable',
									params: {
										name: dataSource.doc.name,
										table: table.name,
									},
								}"
								class="flex cursor-pointer items-center rounded-md px-4 py-3 hover:bg-gray-50"
							>
								<p class="mr-4">
									<Input type="checkbox" class="rounded-md border-gray-300" />
								</p>
								<p
									class="flex flex-1 flex-col whitespace-nowrap text-sm font-medium text-gray-900"
								>
									<span>{{ table.label }}</span>
								</p>
								<p class="flex-1 whitespace-nowrap text-sm text-gray-500">
									<Badge :color="table.hidden ? 'yellow' : 'green'">
										{{ table.hidden ? 'Disabled' : 'Enabled' }}
									</Badge>
								</p>
							</router-link>
						</li>
					</ul>
					<div
						v-if="tables.length == 0"
						class="mt-2 flex h-full w-full flex-col items-center justify-center rounded-md text-base font-light text-gray-500"
					>
						<div class="text-base font-light text-gray-500">
							Tables are not synced yet.
						</div>
						<div
							class="cursor-pointer text-sm font-light text-blue-500 hover:underline"
							@click="syncTables"
						>
							Sync Tables?
						</div>
					</div>
					<div class="flex w-full border-t px-4 py-2 text-sm text-gray-500">
						<p class="ml-auto">
							Showing {{ tables.length }} of
							{{ dataSource.tables.length }}
						</p>
					</div>
				</div>
			</div>
		</template>
	</BasePage>

	<ImportDialog
		:data-source="props.name"
		:show="showImportDialog"
		@close="showImportDialog = false"
	></ImportDialog>
</template>

<script setup>
import { Badge, Dropdown } from 'frappe-ui'
import BasePage from '@/components/BasePage.vue'
import { useDataSource } from '@/datasource/useDataSource'
import { ref, computed, inject } from 'vue'
import ImportDialog from '@/components/ImportDialog.vue'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
})

const dataSource = useDataSource(props.name)
dataSource.fetch_tables()

const statusFilter = ref('Enabled')
const labelFilter = ref('')
const tables = computed(() => {
	return dataSource.tables
		.filter(({ hidden, label }) => {
			const statusMatch =
				statusFilter.value == 'All'
					? true
					: statusFilter.value == 'Enabled'
					? !hidden
					: hidden
			const labelMatch = label.toLowerCase().includes(labelFilter.value.toLowerCase())
			return statusMatch && labelMatch
		})
		.slice(0, 100)
})

const showImportDialog = ref(false)

const $notify = inject('$notify')
function syncTables() {
	dataSource
		.sync_tables()
		.catch((err) => $notify({ title: 'Error Syncing Tables', appearance: 'error' }))
}
</script>
