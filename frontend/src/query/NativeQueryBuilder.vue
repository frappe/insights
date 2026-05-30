<script setup>
import { inject, ref, watch, computed } from 'vue'
import ResultSection from './ResultSection.vue'
import ResultFooter from './visual/ResultFooter.vue'
import NativeQueryEditor from './NativeQueryEditor.vue'

const query = inject('query')
const nativeQuery = ref(query.doc.sql)

const executionTime = computed(() => query.doc.execution_time)
const queriedRowCount = computed(() => query.doc.results_row_count)
const displayedRowCount = computed(() => Math.min(query.MAX_ROWS, queriedRowCount.value))
</script>

<template>
	<div class="flex h-full w-full flex-col pt-2">
		<div class="flex-shrink-0 uppercase leading-7 tracking-wide text-gray-600">
			Native Query
		</div>
		<div class="flex flex-1 flex-shrink-0 overflow-hidden rounded border">
			<NativeQueryEditor />
		</div>
		<div class="flex w-full flex-1 flex-shrink-0 overflow-hidden py-4">
			<ResultSection>
				<template #footer>
					<div class="flex justify-between">
						<div v-if="queriedRowCount >= 0" class="flex items-center space-x-1">
							<span class="text-gray-600">Showing</span>
							<span class="font-mono"> {{ displayedRowCount }}</span>
							<span class="text-gray-600">out of</span>
							<span class="font-mono">{{ queriedRowCount }}</span>
							<span class="text-gray-600">rows in</span>
							<span class="font-mono">{{ executionTime }}</span>
							<span class="text-gray-600">seconds</span>
						</div>
						<Button
							variant="ghost"
							class="ml-1"
							icon="download"
							@click="query.downloadResults"
						>
						</Button>
					</div>
				</template>
			</ResultSection>
		</div>
	</div>
</template>
