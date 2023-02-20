<template>
	<BasePage v-if="query.doc">
		<template #header>
			<!-- Height 2.5 rem -->
			<div class="flex flex-1 items-center">
				<QueryHeader />
			</div>
		</template>

		<template #main>
			<div
				class="main flex flex-1 flex-col overflow-scroll rounded-md scrollbar-hide lg:overflow-hidden"
			>
				<QueryBuilder />
			</div>
		</template>
	</BasePage>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'
import QueryBuilder from '@/components/Query/QueryBuilder.vue'
import QueryHeader from '@/components/Query/QueryHeader.vue'
import { updateDocumentTitle } from '@/utils'
import { useQuery } from '@/utils/query'
import { computed, provide } from 'vue'

const props = defineProps(['name'])
const query = useQuery(props.name)
provide('query', query)
const pageMeta = computed(() => {
	return {
		title: props.name,
		subtitle: 'Query',
	}
})
updateDocumentTitle(pageMeta)
</script>
