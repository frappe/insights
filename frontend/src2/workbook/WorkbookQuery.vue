<script setup lang="ts">
import { computed, inject } from 'vue'
import Query from '../query/Query.vue'
import { Workbook, workbookKey } from './workbook'
import WorkbookQueryEmptyState from './WorkbookQueryEmptyState.vue'

const props = defineProps<{ name?: string; index: number | string }>()

const workbook = inject<Workbook>(workbookKey)
const activeQuery = computed(() => workbook?.doc.queries[Number(props.index)])

const typeIsSet = computed(() => {
	return (
		activeQuery.value?.is_native_query ||
		activeQuery.value?.is_script_query ||
		activeQuery.value?.is_builder_query ||
		activeQuery.value?.operations.find((op) => op.type === 'source')
	)
})

function setQueryType(interfaceType: 'query-builder' | 'sql-editor' | 'script-editor') {
	if (!activeQuery.value) return
	activeQuery.value.is_native_query = interfaceType === 'sql-editor'
	activeQuery.value.is_script_query = interfaceType === 'script-editor'
	activeQuery.value.is_builder_query = interfaceType === 'query-builder'
}
</script>

<template>
	<WorkbookQueryEmptyState v-if="activeQuery && !typeIsSet" @select="setQueryType" />
	<Query v-if="activeQuery && typeIsSet" :key="activeQuery.name" :query="activeQuery" />
</template>
