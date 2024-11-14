<script setup lang="ts">
import { inject } from 'vue'
import { Query } from '../query'
import QueryBuilderSourceSelector from './QueryBuilderSourceSelector.vue'
import QueryBuilderTable from './QueryBuilderTable.vue'
import QueryBuilderToolbar from './QueryBuilderToolbar.vue'
import QueryInfo from './QueryInfo.vue'
import QueryOperations from './QueryOperations.vue'

const query = inject<Query>('query')!
</script>

<template>
	<div class="flex flex-1 overflow-hidden">
		<div class="relative flex h-full flex-1 flex-col gap-3 overflow-hidden p-4">
			<QueryBuilderSourceSelector v-if="!query.doc.operations.length" />
			<template v-else>
				<QueryBuilderToolbar></QueryBuilderToolbar>
				<QueryBuilderTable></QueryBuilderTable>
			</template>
		</div>
		<div
			class="relative z-[1] flex h-full w-[19rem] flex-shrink-0 flex-col overflow-y-auto bg-white"
		>
			<QueryInfo />
			<QueryOperations />
		</div>
	</div>
</template>
