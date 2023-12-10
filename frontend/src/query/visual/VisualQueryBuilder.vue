<script setup>
import Tabs from '@/components/Tabs.vue'
import useResizer from '@/utils/resizer'
import { useStorage } from '@vueuse/core'
import { LoadingIndicator } from 'frappe-ui'
import { inject, onMounted, provide, ref } from 'vue'
import ChartOptions from '../ChartOptions.vue'
import ChartSection from '../ChartSection.vue'
import ResultSection from '../ResultSection.vue'
import ColumnSection from './ColumnSection.vue'
import FilterSection from './FilterSection.vue'
import ResultColumnActions from './ResultColumnActions.vue'
import ResultFooter from './ResultFooter.vue'
import TableSection from './TableSection.vue'
import TransformSection from './TransformSection.vue'
import useAssistedQuery from './useAssistedQuery'

const activeTab = ref('Build')
const tabs = ['Build', 'Visualize']

const query = inject('query')
const assistedQuery = useAssistedQuery(query)
provide('assistedQuery', assistedQuery)

const resizing = ref(false)
const resizeHandle = ref(null)
const chartContainer = ref(null)
const chartContainerHeight = useStorage('insights:chartContainerHeight', undefined)
onMounted(() => {
	useResizer({
		disabled: false,
		direction: 'y',
		handle: resizeHandle.value,
		target: resizeHandle.value.previousElementSibling,
		onResize(width, height) {
			chartContainerHeight.value = height
		},
	})
})
</script>

<template>
	<div class="relative flex h-full w-full flex-row-reverse overflow-hidden border-t">
		<div
			v-if="query.loading"
			class="absolute inset-0 z-[100] flex items-center justify-center bg-gray-100/50"
		>
			<LoadingIndicator class="w-10 text-gray-600" />
		</div>
		<div class="flex h-full w-full flex-col overflow-hidden p-4 pr-0">
			<div
				ref="chartContainer"
				class="flex h-[60%] !max-h-[60%] flex-shrink-0 flex-col overflow-hidden"
				:style="chartContainerHeight >= 0 ? `height: ${chartContainerHeight}px` : ''"
			>
				<ChartSection
					v-if="isNaN(chartContainerHeight) || chartContainerHeight >= 50"
				></ChartSection>
			</div>
			<div
				ref="resizeHandle"
				class="my-2 mx-auto w-20 cursor-ns-resize rounded-full bg-gray-100 py-1 transition-all"
			></div>
			<div class="flex flex-1 flex-shrink-0 flex-col overflow-hidden">
				<ResultSection>
					<template #columnActions="{ column }">
						<ResultColumnActions :column="column" />
					</template>
					<template #footer>
						<ResultFooter></ResultFooter>
					</template>
				</ResultSection>
			</div>
		</div>

		<div
			class="relative flex w-[23rem] flex-shrink-0 flex-col overflow-y-scroll border-r bg-white p-4 pt-0 pl-1"
		>
			<div class="sticky top-0 z-10 w-full flex-shrink-0 bg-white py-4">
				<Tabs v-model="activeTab" class="w-full" :tabs="tabs" />
			</div>
			<div class="space-y-4">
				<template v-if="activeTab === 'Build'">
					<TableSection></TableSection>
					<hr class="border-gray-200" />
					<FilterSection></FilterSection>
					<hr class="border-gray-200" />
					<ColumnSection></ColumnSection>
					<hr class="border-gray-200" />
					<TransformSection></TransformSection>
				</template>
				<template v-if="activeTab === 'Visualize'">
					<ChartOptions></ChartOptions>
				</template>
			</div>
		</div>
	</div>
</template>
