<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import VueGridLayout from '../dashboard/VueGridLayout.vue'
import { __ } from '../translation'
import { fetchDashboard, ViewerDashboard, ViewerFilters } from './viewer'
import ViewerChart from './ViewerChart.vue'

// The whole page body of a desk dashboard page. The layout arrives in one
// request and is drawn straight away; every card then fetches on its own, so
// one slow or failing card never holds up the rest.
const props = defineProps<{ dashboard: string; filters?: ViewerFilters }>()

const doc = ref<ViewerDashboard>()
const loading = ref(true)
const unavailable = ref(false)

// A dashboard that is missing and one the viewer may not read answer the same,
// so there is one page state for both.
async function load() {
	loading.value = true
	unavailable.value = false
	try {
		doc.value = await fetchDashboard(props.dashboard)
	} catch (error) {
		doc.value = undefined
		unavailable.value = true
	} finally {
		loading.value = false
	}
}

watch(() => props.dashboard, load, { immediate: true })

// Filter items hold their place in the saved layout but a viewer has nothing to
// draw them with yet — the filter bar is its own surface, not a grid cell.
// Dropping them lets the grid compact the gap away.
const items = computed(() => (doc.value?.items || []).filter((item) => item.type !== 'filter'))
</script>

<template>
	<div class="w-full">
		<div
			v-if="unavailable"
			class="flex min-h-64 w-full items-center justify-center p-4 text-p-base text-ink-gray-5"
		>
			{{ __('This dashboard is not available') }}
		</div>

		<div v-else-if="loading" class="p-4">
			<div class="h-8 w-64 animate-pulse rounded bg-surface-gray-2" />
		</div>

		<template v-else-if="doc">
			<div class="flex items-center px-4 pt-4">
				<h1 class="text-lg font-medium text-ink-gray-8">{{ doc.title }}</h1>
			</div>

			<div
				v-if="!items.length"
				class="flex min-h-64 w-full items-center justify-center p-4 text-p-base text-ink-gray-5"
			>
				{{ __('This dashboard is empty') }}
			</div>

			<VueGridLayout
				v-else
				class="h-fit w-full p-4"
				:cols="20"
				:disabled="true"
				:verticalCompact="doc.vertical_compact_layout"
				:modelValue="items.map((item) => item.layout)"
			>
				<template #item="{ index }">
					<div class="flex h-full w-full items-center justify-start p-2">
						<ViewerChart
							v-if="items[index].type === 'chart'"
							:chart="items[index].chart!"
							:dashboard="doc.name"
							:filters="props.filters"
						/>
						<div
							v-else-if="items[index].type === 'text'"
							class="prose prose-v3 h-full w-full max-w-none overflow-auto text-ink-gray-7"
							v-html="items[index].text"
						/>
					</div>
				</template>
			</VueGridLayout>
		</template>
	</div>
</template>
