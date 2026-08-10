<script setup lang="ts">
import { ArrowUpRight, Plus } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { getUniqueId } from '../helpers'
import { __ } from '../translation'

const router = useRouter()
function openNewWorkbook() {
	const unique_id = getUniqueId()
	const name = `new-workbook-${unique_id}`
	router.push(`/workbook/${name}`)
}
</script>

<template>
	<div>
		<div class="flex items-center space-x-2">
			<div class="rounded-4 bg-surface-gray-2 p-1">
				<ArrowUpRight class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
			</div>
			<div class="text-lg">{{ __('Quick Actions') }}</div>
		</div>
		<div class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
			<div
				class="col-span-1 flex cursor-pointer items-center justify-between rounded-4 border border-transparent bg-surface-base p-4 shadow transition-all hover:border-outline-gray-3"
				@click="openNewWorkbook"
			>
				<div class="text-lg-medium text-ink-gray-8">{{ __('New Workbook') }}</div>
				<div class="rounded-4 bg-surface-gray-2 p-1">
					<Plus class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
				</div>
			</div>
		</div>
	</div>
</template>
