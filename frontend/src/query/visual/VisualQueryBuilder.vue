<script setup>
import Tabs from '@/components/Tabs.vue'
import { LoadingIndicator } from 'frappe-ui'
import { inject, provide, ref, watch } from 'vue'
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
</script>

<template>
	<div class="relative flex h-full w-full flex-row-reverse overflow-hidden border-t">
		<div
			v-if="query.loading"
			class="absolute inset-0 z-10 flex items-center justify-center bg-gray-100/50"
		>
			<LoadingIndicator class="w-10 text-gray-600" />
		</div>
		<div class="flex h-full w-full flex-col space-y-4 overflow-hidden p-4 pr-0">
			<div class="flex flex-[3] flex-shrink-0 flex-col overflow-hidden">
				<ChartSection></ChartSection>
			</div>
			<div class="flex flex-[2] flex-shrink-0 flex-col overflow-hidden">
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
			class="flex w-[21rem] flex-shrink-0 flex-col space-y-4 overflow-y-scroll border-r bg-white p-4 pl-0"
		>
			<Tabs v-model="activeTab" class="w-full flex-shrink-0" :tabs="tabs" />
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
</template>
