<template>
	<BasePage>
		<template #header>
			<div v-if="dataSourceTable.doc" class="flex flex-1 justify-between">
				<div class="flex items-center space-x-4">
					<h1 class="text-3xl font-medium text-gray-900">
						{{ dataSourceTable.doc.label }}
					</h1>
					<Badge :color="hidden ? 'yellow' : 'green'" class="h-fit">
						{{ hidden ? 'Disabled' : 'Enabled' }}
					</Badge>
				</div>
				<div class="space-x-2">
					<Dropdown
						placement="right"
						:button="{ icon: 'more-horizontal', appearance: 'white' }"
						:options="[
							{
								label: hidden ? 'Enable' : 'Disable',
								icon: hidden ? 'eye' : 'eye-off',
								handler: () => (hidden = !hidden),
							},
						]"
					/>
				</div>
			</div>
		</template>
		<template #main>
			<div v-if="dataSourceTable.columns" class="flex h-full flex-1 flex-col">
				<div class="mb-4 flex space-x-4">
					<Input type="text" placeholder="Status" />
				</div>
				<div class="flex h-[calc(100%-3rem)] flex-col rounded-md border">
					<!-- List Header -->
					<div
						class="flex items-center justify-between border-b py-3 px-4 text-sm text-gray-500"
					>
						<p class="mr-4">
							<Input type="checkbox" class="rounded-md border-gray-400" />
						</p>
						<p
							class="flex-1"
							v-for="column in dataSourceTable.columns.slice(0, MAX_COLS)"
						>
							{{ column[0] }}
						</p>
					</div>
					<ul
						role="list"
						class="flex flex-1 flex-col divide-y divide-gray-200 overflow-y-scroll"
					>
						<li v-for="row in dataSourceTable.data">
							<a
								class="flex cursor-pointer items-center rounded-md py-3 px-4 hover:bg-gray-50"
							>
								<p class="mr-4">
									<Input type="checkbox" class="rounded-md border-gray-400" />
								</p>
								<p
									v-for="value in row.slice(0, MAX_COLS)"
									class="flex-1 whitespace-nowrap text-sm text-gray-500"
								>
									{{ value }}
								</p>
							</a>
						</li>
					</ul>
					<div class="flex w-full border-t px-4 py-2 text-sm text-gray-500">
						<p class="ml-auto">
							Showing {{ dataSourceTable.data.length }} of
							{{ dataSourceTable.data.length }}
						</p>
					</div>
				</div>
			</div>
		</template>
	</BasePage>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'
import { useDataSourceTable } from '@/utils/datasource'
import { Dropdown, Badge } from 'frappe-ui'
import { computed } from 'vue'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
	table: {
		type: String,
		required: true,
	},
})

const MAX_COLS = 8

const dataSourceTable = useDataSourceTable(props.name, props.table)
const hidden = computed({
	get() {
		return dataSourceTable.doc.hidden
	},
	set(value) {
		if (value !== dataSourceTable.doc.hidden) {
			dataSourceTable.doc.hidden = value
			dataSourceTable.updateVisibility(value)
		}
	},
})
</script>
