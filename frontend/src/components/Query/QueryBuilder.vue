<template>
	<div class="flex h-full min-h-[16rem] w-full flex-shrink-0 flex-col rounded-md bg-white text-base text-gray-700">
		<div class="flex h-[calc(100%-2.5rem)] divide-x pt-4">
			<TablePicker :query="query" />
			<ColumnPicker :query="query" />
			<FilterPicker :query="query" />
		</div>
		<div class="flex h-10 flex-shrink-0 border-t">
			<LimitsAndOrder :query="query" />
		</div>
	</div>
</template>

<script>
// import QueryToolbar from '@/components/QueryToolbar.vue'
// import QueryResult from '@/components/QueryResult.vue'
import LimitsAndOrder from '@/components/Query/LimitsAndOrder.vue'
import TablePicker from '@/components/Query/TablePicker.vue'
import ColumnPicker from '@/components/Query/ColumnPicker.vue'
import FilterPicker from '@/components/Query/FilterPicker.vue'

export default {
	name: 'QueryBuilder',
	props: ['query'],
	components: {
		// QueryToolbar,
		// QueryResult,
		LimitsAndOrder,
		TablePicker,
		ColumnPicker,
		FilterPicker,
	},
}
</script>
