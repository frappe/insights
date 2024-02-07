<script setup>
import { call } from 'frappe-ui'
import { inject, ref } from 'vue'
import { useRouter } from 'vue-router'

const $dayjs = inject('$dayjs')

const recent_records = ref([])
call('insights.api.home.get_last_viewed_records').then((data) => {
	recent_records.value = data.map((d) => {
		const record_type = d.reference_doctype.replace('Insights ', '')
		const routeName = record_type.replace(' ', '')
		return {
			title: d.title,
			type: record_type,
			name: d.reference_name,
			notebook: d.notebook,
			last_viewed: $dayjs(d.creation).format('MMM DD, YYYY hh:mm A'),
			last_viewed_from_now: `Last viewed ${$dayjs(d.creation).fromNow()}`,
		}
	})
})

const router = useRouter()
function openRecord(row) {
	const { type, notebook, name } = row
	switch (type) {
		case 'Notebook Page':
			return router.push(`/notebook/${notebook}/${name}`)
		case 'Dashboard':
			return router.push(`/dashboard/${name}`)
		case 'Query':
			return router.push(`/query/build/${name}`)
		default:
			break
	}
}
</script>

<template>
	<div class="flex h-full flex-col overflow-hidden">
		<div class="flex items-center space-x-2">
			<div class="rounded bg-gray-100 p-1">
				<FeatherIcon name="clock" class="h-4 w-4" />
			</div>
			<div class="text-lg">Recently Viewed</div>
		</div>
		<div class="mt-3 flex-1 overflow-hidden p-1">
			<!-- list of recent records -->
			<ul
				v-if="recent_records?.length > 0"
				class="relative flex flex-1 flex-col overflow-y-auto"
			>
				<li class="border-b"></li>
				<li
					v-for="(row, idx) in recent_records"
					:key="idx"
					class="flex cursor-pointer items-center gap-4 border-b transition-colors hover:bg-gray-50"
					@click="openRecord(row)"
				>
					<div>
						<FeatherIcon name="arrow-up-right" class="h-4 w-4 text-gray-600" />
					</div>
					<div
						v-for="(key, idx) in ['title', 'type', 'last_viewed_from_now']"
						class="overflow-hidden text-ellipsis whitespace-nowrap py-3"
						:class="[idx === 0 ? 'w-[30%] ' : 'flex-1 text-gray-600']"
					>
						<span>
							{{ row[key] }}
						</span>
					</div>
				</li>
			</ul>

			<!-- empty state -->
			<div v-else class="flex h-full w-full items-center justify-center">
				<div class="flex flex-col items-center space-y-2">
					<div class="text-lg text-gray-600">No recent records</div>
					<div class="text-sm text-gray-600">
						You can view your recently viewed records here
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
