<script setup lang="ts">
import { DatabaseZap, Table } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import { Query } from '../query'
import SourceSelectorDialog from './source_selector/SourceSelectorDialog.vue'

const query = inject('query') as Query
const showSourceSelectorDialog = ref(true)
</script>

<template>
	<div class="flex h-full w-full items-center justify-center bg-gray-50">
		<div class="flex items-center gap-4">
			<div
				class="flex h-[18rem] w-[24rem] flex-col items-center justify-center rounded bg-white px-8 text-center shadow-sm"
			>
				<DatabaseZap class="mb-2 h-12 w-12 text-gray-400" stroke-width="1.5" />
				<span class="px-12 text-sm text-gray-600">
					Select a source table to start building your query
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
