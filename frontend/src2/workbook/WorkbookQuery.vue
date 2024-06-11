<script setup lang="ts">
import { computed, inject } from 'vue'
import QueryBuilder from '../query/QueryBuilder.vue'
import { Workbook, workbookKey } from './workbook'

const props = defineProps<{ name?: string; index: number | string }>()
const workbook = inject(workbookKey) as Workbook
workbook.setActiveTab('query', Number(props.index))
</script>

<template>
	<QueryBuilder
		v-if="workbook.activeQuery"
		:key="workbook.activeQuery.name"
		:query="workbook.activeQuery"
	/>
</template>
