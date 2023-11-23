<script setup>
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import Tabs from '@/components/Tabs.vue'
import { provide, ref, watchEffect } from 'vue'
import ChartOptions from './ChartOptions.vue'
import ChartSection from './ChartSection.vue'
import NativeQueryBuilder from './NativeQueryBuilder.vue'
import QueryHeader from './QueryHeader.vue'
import ScriptQueryEditor from './ScriptQueryEditor.vue'
import ClassicQueryBuilder from './deprecated/ClassicQueryBuilder.vue'
import useQuery from './resources/useQuery'
import VisualQueryBuilder from './visual/VisualQueryBuilder.vue'

const props = defineProps({ name: String })
const query = useQuery(props.name)
await query.reload()
provide('query', query)

const activeTab = ref('Query')
const tabs = ['Query', 'Visualize']

watchEffect(() => {
	if (query.doc?.name) {
		document.title = `${query.doc.name} - Frappe Insights`
	}
})
</script>

<template>
	<header class="sticky top-0 z-10 flex items-center justify-between bg-white px-5 py-2.5">
		<PageBreadcrumbs
			class="h-7"
			:items="[
				{ label: 'Queries', route: { path: '/query' } },
				{
					label: props.name,
					route: { path: `/query/build/${props.name}` },
				},
			]"
		/>
	</header>
	<div
		v-if="query.doc?.name"
		class="flex h-full w-full flex-col space-y-4 overflow-hidden bg-white px-6 pt-2"
	>
		<div class="w-full flex-shrink-0">
			<QueryHeader>
				<template v-if="!query.doc.is_assisted_query" #right-actions>
					<Tabs v-model="activeTab" :tabs="tabs" />
				</template>
			</QueryHeader>
		</div>
		<div v-if="activeTab == 'Query'" class="flex flex-1 flex-shrink-0 overflow-hidden">
			<VisualQueryBuilder v-if="query.doc.is_assisted_query"></VisualQueryBuilder>
			<NativeQueryBuilder v-else-if="query.doc.is_native_query"></NativeQueryBuilder>
			<ScriptQueryEditor v-else-if="query.doc.is_script_query"></ScriptQueryEditor>
			<ClassicQueryBuilder
				v-else-if="
					!query.doc.is_assisted_query &&
					!query.doc.is_native_query &&
					!query.doc.is_script_query
				"
			/>
		</div>
		<div
			v-if="activeTab == 'Visualize' && query.chart.doc?.name"
			class="flex flex-1 flex-shrink-0 gap-4 overflow-hidden"
		>
			<div class="w-[21rem] flex-shrink-0">
				<ChartOptions></ChartOptions>
			</div>
			<div class="flex flex-1">
				<ChartSection></ChartSection>
			</div>
		</div>
	</div>
</template>
