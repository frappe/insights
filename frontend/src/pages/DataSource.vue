<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1 items-center justify-between">
				<h1 v-if="dataSource.doc" class="text-3xl font-medium text-gray-900">
					{{ dataSource.doc.title }}
				</h1>
			</div>
		</template>
		<template #main>
			<div v-if="dataSource.tables" class="flex flex-1 flex-col pt-2">
				<div class="mb-4 flex space-x-4">
					<Input type="text" placeholder="Label" v-model="labelFilter" />
					<Input
						type="select"
						placeholder="Status"
						v-model="statusFilter"
						:options="['Disabled', 'Enabled', 'All']"
					/>
				</div>
				<div class="flex h-[calc(100%-3rem)] flex-col rounded-md border">
					<!-- List Header -->
					<div
						class="flex items-center justify-between border-b py-3 px-4 text-sm text-gray-500"
					>
						<p class="mr-4">
							<Input type="checkbox" class="rounded-md border-gray-400" />
						</p>
						<p class="flex-1">Table</p>
						<p class="flex-1">Status</p>
					</div>
					<ul
						role="list"
						class="flex flex-1 flex-col divide-y divide-gray-200 overflow-y-scroll"
					>
						<li v-for="table in tables" :key="table.table">
							<router-link
								:to="{
									name: 'DataSourceTable',
									params: {
										name: dataSource.doc.name,
										table: table.table,
									},
								}"
								class="flex cursor-pointer items-center rounded-md py-3 px-4 hover:bg-gray-50"
							>
								<p class="mr-4">
									<Input type="checkbox" class="rounded-md border-gray-400" />
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
					<div class="flex w-full border-t px-4 py-2 text-sm text-gray-500">
						<p class="ml-auto">
							Showing {{ tables.length }} of {{ dataSource.tables.length }}
						</p>
					</div>
				</div>
			</div>
		</template>
	</BasePage>
</template>

<script setup>
import { Badge } from 'frappe-ui'
import BasePage from '@/components/BasePage.vue'
import { useDataSource } from '@/utils/datasource'
import { ref, computed } from 'vue'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
})

const dataSource = useDataSource(props.name)

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
</script>
