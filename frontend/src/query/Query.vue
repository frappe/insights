<template>
	<div v-if="query.doc" class="flex flex-1 flex-col overflow-hidden">
		<div class="flex flex-shrink-0 items-center justify-between px-2 pb-2">
			<QueryHeader />
			<Tabs v-if="!hideTabs" class="!w-40" :tabs="tabs" @switch="switchTab" />
		</div>
		<div class="flex flex-1 flex-shrink-0 flex-col overflow-y-scroll">
			<template v-if="activeTab == buildTabLabel">
				<div
					v-if="query.doc.is_native_query"
					class="flex min-h-[20rem] flex-1 flex-shrink-0 gap-4 overflow-hidden px-2 py-1"
				>
					<NativeQueryEditor />
				</div>
				<div
					v-else-if="query.doc.is_script_query"
					class="flex min-h-[20rem] flex-1 flex-shrink-0 gap-4 overflow-hidden px-2 py-1"
				>
					<ScriptQueryEditor />
				</div>
				<div
					v-else
					class="flex min-h-[20rem] flex-1 flex-shrink-0 gap-4 overflow-hidden px-2 py-1"
				>
					<template v-if="!query.doc.is_assisted_query">
						<TablePanel />
						<ColumnPanel />
						<FilterPanel />
					</template>
					<template v-else>
						<div class="flex min-h-[20rem] w-full flex-1 rounded border py-2">
							<Suspense>
								<VisualQuery :name="query.doc.name" />
							</Suspense>
						</div>
					</template>
				</div>
				<QueryResult class="min-h-[20rem] flex-1" />
			</template>

			<template v-if="activeTab == 'Visualize'">
				<QueryVisualizer class="flex-1" />
			</template>
		</div>
	</div>
</template>

<script setup>
import Tabs from '@/components/Tabs.vue'
import { default as VisualQuery } from '@/notebook/blocks/query/builder/QueryBuilder.vue'
import ColumnPanel from '@/query/Column/ColumnPanel.vue'
import FilterPanel from '@/query/Filter/FilterPanel.vue'
import NativeQueryEditor from '@/query/NativeQueryEditor.vue'
import ScriptQueryEditor from '@/query/ScriptQueryEditor.vue'
import QueryHeader from '@/query/QueryHeader.vue'
import QueryVisualizer from '@/query/QueryVisualizer.vue'
import QueryResult from '@/query/Result/QueryResult.vue'
import TablePanel from '@/query/Table/TablePanel.vue'
import { updateDocumentTitle } from '@/utils'
import { useQuery } from '@/utils/query'
import { computed, provide, ref } from 'vue'

const props = defineProps(['name', 'hideTabs'])
const query = useQuery(props.name)
provide('query', query)

const buildTabLabel = computed(() => (query.doc?.is_native_query ? 'Write' : 'Build'))
const tabs = ref([
	{ label: buildTabLabel, active: true },
	{ label: 'Visualize', active: false },
])
const activeTab = computed(() => tabs.value.find((t) => t.active).label)
const switchTab = (tab) => {
	tabs.value.forEach((t) => {
		t.active = t.label === tab.label
	})
}

const pageMeta = computed(() => ({
	title: query.doc?.title,
	subtitle: query.doc?.name,
}))
updateDocumentTitle(pageMeta)
</script>
