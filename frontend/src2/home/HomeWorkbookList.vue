<script setup lang="ts">
import { Avatar, createListResource } from 'frappe-ui'
import { ArrowUpRight, Book } from 'lucide-vue-next'
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from '../helpers/dayjs'

const router = useRouter()

const workbooks = createListResource({
	cache: 'insights_workbooks',
	doctype: 'Insights Workbook',
	fields: ['name', 'title', 'owner', 'creation'],
	pageLength: 20,
	auto: true,
})

const searchQuery = ref('')
watch(searchQuery, (query) => {
	workbooks.filters = query
		? {
				title: ['like', `%${query}%`],
		  }
		: {}
	workbooks.reload()
})
</script>

<template>
	<div class="flex h-full flex-col overflow-hidden">
		<div class="flex items-center space-x-2">
			<div class="rounded bg-gray-100 p-1">
				<Book class="h-4 w-4 text-gray-700" stroke-width="1.5" />
			</div>
			<div class="text-lg">Workbooks</div>
		</div>
		<div class="mt-3 flex-1 overflow-hidden p-1">
			<!-- list of recent records -->
			<ul
				v-if="workbooks.list.data?.length > 0"
				class="relative flex flex-1 flex-col overflow-y-auto"
			>
				<li class="border-b"></li>
				<li
					v-for="(row, idx) in workbooks.list.data"
					:key="idx"
					class="flex h-10 cursor-pointer items-center gap-4 border-b transition-colors hover:bg-gray-50"
					@click="router.push(`/workbook/${row.name}`)"
				>
					<ArrowUpRight class="h-4 w-4 text-gray-700" stroke-width="1.5" />
					<div class="w-[50%] truncate">{{ row.title }}</div>
					<div class="flex-1 text-sm text-gray-500">
						<Avatar :label="row.owner" />
						<span class="ml-1.5">{{ row.owner }}</span>
					</div>
					<div class="flex-1 text-sm text-gray-500">
						{{ (dayjs(row.creation) as any).fromNow() }}
					</div>
				</li>
			</ul>

			<!-- empty state -->
			<div v-else class="flex h-full w-full items-center justify-center">
				<div class="flex flex-col items-center space-y-2">
					<div class="text-lg text-gray-600">No workbooks created</div>
					<div class="text-sm text-gray-600">
						Your workbooks will appear here. Create a new workbook to get started.
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
