<script setup>
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import { provide, ref, watchEffect } from 'vue'
import QueryHeader from '../QueryHeader.vue'
import QueryHeaderTitle from '../QueryHeaderTitle.vue'
import useQuery from '../resources/useQuery'
import VisualQueryBuilder from './VisualQueryBuilder.vue'

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
				{ label: 'Query Builder', route: { path: '/query' } },
				// { component: QueryHeaderTitle },
			]"
		/>
	</header>
	<div
		v-if="query.doc?.name"
		class="flex h-full w-full flex-col space-y-4 overflow-hidden bg-white"
	>
		<VisualQueryBuilder v-if="query.doc.is_assisted_query"></VisualQueryBuilder>
	</div>
</template>
./pipeline_example
