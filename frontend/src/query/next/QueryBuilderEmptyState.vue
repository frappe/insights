<script setup lang="ts">
import { Table } from 'lucide-vue-next'
import { inject } from 'vue'
import { Query } from './useQuery'

const query = inject('query') as Query
</script>

<template>
	<div class="flex h-full w-full items-center justify-center">
		<div class="flex items-center gap-4">
			<div
				class="flex h-[18rem] w-[24rem] flex-col items-center justify-center rounded border px-8 text-center"
			>
				<Table class="mb-2 h-12 w-12 text-gray-400" stroke-width="1.5" />
				<span class="text-lg font-medium">Select a Source</span>
				<span class="text-sm text-gray-600">
					Select a source to start building your query
				</span>
				<Button
					class="mt-2"
					variant="outline"
					@click="query.showSourceSelectorDialog = true"
				>
					Open Source Selector
				</Button>
			</div>
		</div>
	</div>
</template>
