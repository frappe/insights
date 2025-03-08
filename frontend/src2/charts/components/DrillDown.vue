<script setup lang="ts">
import { wheneverChanges } from '../../helpers'
import QueryDataTable from '../../query/components/QueryDataTable.vue'
import { Query } from '../../query/query'

const props = defineProps<{ query: Query }>()

const show = defineModel()
wheneverChanges(show, () => show.value && props.query.execute(), { immediate: true })
</script>

<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Drill Down Results',
			size: '5xl',
		}"
	>
		<template #body-content>
			<div
				class="relative flex h-[32rem] w-full flex-1 flex-col overflow-hidden rounded border bg-white"
			>
				<QueryDataTable :enable-sort="true" :enable-drill-down="true" :query="props.query">
				</QueryDataTable>
			</div>
		</template>
	</Dialog>
</template>
