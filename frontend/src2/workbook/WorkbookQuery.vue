<script setup lang="ts">
import { inject, ref } from 'vue'
import Query from '../query/Query.vue'
import { workbookKey } from './workbook'
import { useRouter } from 'vue-router'

const props = defineProps<{ workbook_name?: string; query_name: string }>()

const router = useRouter()
const workbook = inject(workbookKey)!

let query_name = ref(props.query_name)
const index = Number(props.query_name)
if (
	index >= 0 &&
	workbook.doc.queries[index] &&
	!workbook.doc.queries.find((q) => q.name === props.query_name)
) {
	query_name.value = workbook.doc.queries[index].name
	router.replace(`/workbook/${workbook.doc.name}/query/${query_name.value}`)
}
</script>

<template>
	<Query :query_name="query_name" />
</template>
