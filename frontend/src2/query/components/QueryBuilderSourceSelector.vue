<script setup lang="ts">
import { DatabaseZap } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import { Query } from '../query'
import SourceSelectorDialog from './source_selector/SourceSelectorDialog.vue'

const query = inject('query') as Query
const showSourceSelectorDialog = ref(true)
</script>

<template>
	<div class="flex h-full w-full items-center justify-center">
		<div class="flex items-center gap-4">
			<div
				class="flex flex-col items-center justify-center gap-2 rounded border border-dashed border-gray-300 p-8 text-center"
			>
				<div class="rounded-full bg-orange-50 p-3">
					<DatabaseZap class="h-5 w-5 text-orange-500/70" stroke-width="1.5" />
				</div>
				<p class="font-medium">No Table Selected</p>
				<span class="text-sm leading-4 text-gray-600">
					Select a source table to start building your query.
					<br />
					You can also select a query as a source.
				</span>
				<Button class="mt-2" variant="outline" @click="showSourceSelectorDialog = true">
					Open Selector
				</Button>
			</div>
		</div>
	</div>

	<SourceSelectorDialog
		v-if="showSourceSelectorDialog"
		v-model="showSourceSelectorDialog"
		@select="query.setSource($event)"
	/>
</template>
