<script setup lang="jsx">
import { Play } from 'lucide-vue-next'
import { inject } from 'vue'
import QueryDataSourceSelector from './QueryDataSourceSelector.vue'
import QueryMenu from './QueryMenu.vue'

const query = inject('query')
</script>

<template>
	<div class="flex items-center gap-2">
		<QueryMenu></QueryMenu>
		<QueryDataSourceSelector v-if="!query.doc.is_assisted_query"></QueryDataSourceSelector>
		<Button
			v-if="!query.doc.is_script_query && !query.doc.is_native_query"
			variant="solid"
			@click="query.execute()"
			:loading="query.executing"
			:disabled="!query.doc.data_source || !query.doc.sql"
		>
			<template #prefix>
				<Play class="h-4 w-4"></Play>
			</template>
			<span>Execute</span>
		</Button>
	</div>
</template>
