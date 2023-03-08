<script setup>
import BaseLayout from '@/layouts/BaseLayout.vue'
import Query from '@/query/Query.vue'
import QueryBuilderToolbar from '@/query/QueryBuilderToolbar.vue'
import QueryList from '@/query/QueryList.vue'
import useQueryBuilder from '@/query/useQueryBuilder'
import { updateDocumentTitle } from '@/utils'
import { provide, ref } from 'vue'

const props = defineProps({ name: { type: String } })
const queryBuilder = useQueryBuilder()
if (props.name) queryBuilder.openQuery(props.name)
provide('queryBuilder', queryBuilder)

const pageMeta = ref({ title: 'Query Builder' })
updateDocumentTitle(pageMeta)
</script>

<template>
	<BaseLayout>
		<template #navbar>
			<div class="relative flex w-full flex-shrink-0 items-center space-x-4">
				<p class="px-1 text-xl font-medium">Query Builder</p>
			</div>
		</template>

		<template #content>
			<div
				v-if="!queryBuilder.queries.length"
				class="flex w-full flex-1 items-center justify-center"
			>
				<QueryList @select="(name) => queryBuilder.openQuery(name)" />
			</div>

			<div v-else class="flex w-full flex-1 flex-col overflow-hidden p-3">
				<QueryBuilderToolbar />
				<div
					class="flex w-full flex-1 overflow-hidden rounded-b-md rounded-r-md border bg-white p-2 shadow-sm"
				>
					<Query v-if="queryBuilder.currentQuery" :key="queryBuilder.currentQuery.name" />
				</div>
			</div>
		</template>
	</BaseLayout>

	<Dialog v-model="queryBuilder.showNewDialog">
		<template #body>
			<QueryList @select="(name) => queryBuilder.openQuery(name)" />
		</template>
	</Dialog>
</template>
