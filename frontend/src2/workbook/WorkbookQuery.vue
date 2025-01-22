<script setup lang="ts">
import Query from '../query/Query.vue'

const props = defineProps<{ workbook_name?: string; query_name: string }>()
</script>

<template>
	<Query :query_name="props.query_name" />
</template>
