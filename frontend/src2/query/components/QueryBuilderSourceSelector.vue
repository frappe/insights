<script setup lang="ts">
import { DatabaseZap, Sparkles } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import { Query } from '../query'
import SourceSelectorDialog from './source_selector/SourceSelectorDialog.vue'
import AIQueryDialog from './AIQueryDialog.vue'

const query = inject('query') as Query
const showSourceSelectorDialog = ref(true)
const showAIQueryDialog = ref(false)
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
				<div class="mt-2 flex gap-2">
					<Button variant="outline" @click="showSourceSelectorDialog = true">
						Open Selector
					</Button>
					<Button variant="outline" @click="showAIQueryDialog = true">
						<template #prefix>
							<Sparkles class="h-3 w-3 text-gray-600" stroke-width="1.5" />
						</template>
						Generate with AI
					</Button>
				</div>
			</div>
		</div>
	</div>

	<SourceSelectorDialog
		v-if="showSourceSelectorDialog"
		v-model="showSourceSelectorDialog"
		@select="query.setSource($event)"
	/>
	<AIQueryDialog v-if="showAIQueryDialog" v-model="showAIQueryDialog" />
</template>
