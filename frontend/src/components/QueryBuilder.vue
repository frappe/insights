<template>
	<div class="h-full min-h-[12rem] flex-1 rounded-md bg-white">
		<div class="flex h-16 flex-shrink-0">
			<QueryToolbar :query="query" />
		</div>
		<div class="flex h-[calc(100%-6.5rem)]">
			<QueryResult :query="query" />
		</div>
		<div class="flex h-10 flex-shrink-0">
			<LimitsAndOrder :query="query" />
		</div>
	</div>
</template>

<script>
import QueryToolbar from '@/components/QueryToolbar.vue'
import QueryResult from '@/components/QueryResult.vue'
import LimitsAndOrder from '@/components/LimitsAndOrder.vue'

export default {
	name: 'QueryBuilder',
	props: ['query'],
	components: {
		QueryToolbar,
		QueryResult,
		LimitsAndOrder,
	},
}
</script>
