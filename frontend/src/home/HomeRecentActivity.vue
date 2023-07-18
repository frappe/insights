<script setup>
import { ref, inject } from 'vue'
import { call } from 'frappe-ui'

const $dayjs = inject('$dayjs')

const activities = ref([])
call('insights.api.get_recent_activity').then((data) => {
	activities.value = data.map((d) => {
		return {
			...d,
			modified: $dayjs(d.modified).fromNow(),
		}
	})
})
</script>

<template>
	<div class="flex flex-col overflow-hidden">
		<div class="flex items-center space-x-2">
			<div class="rounded bg-gray-100 p-1">
				<FeatherIcon name="clock" class="h-4 w-4" />
			</div>
			<div class="text-lg">Activity</div>
		</div>
		<div class="mt-4 flex-1 space-y-6 overflow-y-scroll">
			<div
				v-for="(activity, i) in activities"
				:key="i"
				class="flex w-fit cursor-pointer items-center space-x-4"
			>
				<div class="flex-shrink-0">
					<Avatar size="xl" :label="activity.owner" />
				</div>
				<div class="flex flex-1 flex-col space-y-1">
					<div class="flex items-center space-x-1">
						<div class="font-medium text-gray-900">{{ activity.owner }}</div>
						<div class="text-gray-600">updated</div>
						<div class="font-medium text-gray-900">
							{{ activity.ref_doctype }}
							{{
								activity.docname !== activity.ref_doctype
									? `-- ${activity.docname}`
									: ''
							}}
						</div>
					</div>
					<div class="text-sm text-gray-600">{{ activity.modified }}</div>
				</div>
			</div>
		</div>
	</div>
</template>
