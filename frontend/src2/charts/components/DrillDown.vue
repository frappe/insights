<script setup lang="ts">
import { provide } from 'vue'
import { wheneverChanges } from '../../helpers'
import QueryBuilderToolbar from '../../query/components/QueryBuilderToolbar.vue'
import QueryDataTable from '../../query/components/QueryDataTable.vue'
import QueryOperations from '../../query/components/QueryOperations.vue'
import { Query } from '../../query/query'

const props = defineProps<{ query: Query }>()

const show = defineModel()
wheneverChanges(
	show,
	() => {
		if (show.value && !props.query.result.executedSQL && !props.query.executing) {
			props.query.execute()
		}
	},
	{ immediate: true }
)

provide('query', props.query)
</script>

<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Drill Down',
			size: '5xl',
		}"
	>
		<template #body-content>
			<div class="relative flex h-[32rem] w-full flex-1 gap-4 overflow-hidden bg-white">
				<div class="flex h-full flex-1 flex-col gap-2 overflow-hidden p-0.5">
					<QueryBuilderToolbar></QueryBuilderToolbar>
					<div class="flex flex-1 overflow-hidden rounded border">
						<QueryDataTable
							:enable-sort="true"
							:enable-drill-down="true"
							:query="props.query"
						/>
					</div>
				</div>
				<div
					class="relative z-[1] flex h-full w-[17rem] flex-shrink-0 overflow-y-auto rounded border bg-white"
				>
					<QueryOperations />
				</div>
			</div>
		</template>
	</Dialog>
</template>
