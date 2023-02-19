<script setup>
import QueryBuilder from '@/components/Query/QueryBuilder.vue'
import QueryHeader from '@/components/Query/QueryHeader.vue'
import { useQuery } from '@/utils/query'
import { provide } from 'vue'
const props = defineProps(['name'])
const query = useQuery(props.name)
provide('query', query)
</script>

<template>
	<div v-if="query.doc" class="flex w-full flex-col px-5 py-3">
		<div class="h-fit flex-shrink-0">
			<QueryHeader />
		</div>
		<div class="flex flex-1 overflow-hidden">
			<div
				class="flex flex-1 flex-col overflow-scroll rounded-md scrollbar-hide lg:overflow-hidden"
			>
				<QueryBuilder />
			</div>
		</div>
	</div>
</template>
