<script setup lang="ts">
import { computed, inject } from 'vue'
import QueryBuilder from '../query/QueryBuilder.vue'
import { Workbook, workbookKey } from './workbook'

const props = defineProps<{ name?: string; index: number | string }>()

const workbook = inject<Workbook>(workbookKey)
const activeQuery = computed(() => workbook?.doc.queries[Number(props.index)])
</script>

<template>
	<QueryBuilder v-if="activeQuery" :key="activeQuery.name" :query="activeQuery" />
</template>
