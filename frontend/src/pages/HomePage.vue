<template>
	<div
		class="flex h-[calc(100%)] min-h-[38rem] flex-col items-center justify-center rounded-md bg-gray-100 pb-12"
	>
		<div class="mb-4 text-2xl font-light text-gray-600">Get Started</div>
		<div class="flex flex-col space-y-3 text-center text-base">
			<router-link
				v-for="nav in navigationButtons"
				:to="nav.to"
				class="cursor-pointer rounded border bg-gray-200 px-6 py-1.5 text-gray-600 hover:text-gray-700"
			>
				{{ nav.label }}
			</router-link>
		</div>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { updateDocumentTitle } from '@/utils'

const navigationButtons = ref([
	{
		label: 'Browse data',
		to: { name: 'DataSourceList' },
	},
	{
		label: 'Create query',
		to: { name: 'QueryList' },
	},
	{
		label: 'Create dashboard',
		to: { name: 'DashboardList' },
	},
])

const pageMeta = ref({
	title: 'Get Started',
})
updateDocumentTitle(pageMeta)
</script>
