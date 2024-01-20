<script setup>
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import Tabs from '@/components/Tabs.vue'
import { provide, ref, watchEffect } from 'vue'
import ChartOptions from './ChartOptions.vue'
import ChartSection from './ChartSection.vue'
import NativeQueryBuilder from './NativeQueryBuilder.vue'
import QueryHeader from './QueryHeader.vue'
import QueryHeaderTitle from './QueryHeaderTitle.vue'
import ScriptQueryEditor from './ScriptQueryEditor.vue'
import ClassicQueryBuilder from './deprecated/ClassicQueryBuilder.vue'
import useQuery from './resources/useQuery'
import VisualQueryBuilder from './visual/VisualQueryBuilder.vue'

const props = defineProps({ name: String })
const query = useQuery(props.name)
await query.reload()
provide('query', query)

const activeTab = ref(0)
const tabs = ref([
	{ label: 'Query', value: 0 },
	{ label: 'Visualize', value: 1 },
])

watchEffect(() => {
	if (query.doc?.name) {
		const title = query.doc.title || query.doc.name
		document.title = `${title} - Frappe Insights`
	}
})
</script>

<template>
	<header
		class="sticky top-0 z-10 flex w-full items-center justify-between border-b bg-white px-4 py-2.5"
	>
		<PageBreadcrumbs
			class="h-7"
			:items="[
				{ label: 'Queries', route: { path: '/query' } },
				{ component: QueryHeaderTitle },
			]"
		/>
		<div class="flex gap-2">
			<QueryHeader></QueryHeader>
			<Tabs v-if="!query.doc.is_assisted_query" v-model="activeTab" :tabs="tabs" />
		</div>
	</header>
	<div
		v-if="query.doc?.name"
		class="flex h-full w-full flex-col space-y-4 overflow-hidden bg-white px-4"
	>
		<div v-if="activeTab == 0" class="flex flex-1 flex-shrink-0 overflow-hidden">
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
			v-if="activeTab == 1 && query.chart.doc?.name"
			class="flex flex-1 flex-shrink-0 gap-4 overflow-hidden pt-4"
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
