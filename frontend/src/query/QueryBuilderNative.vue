<script setup>
import QueryResult from '@/query/Result/QueryResult.vue'
import NativeQueryEditor from '@/query/NativeQueryEditor.vue'
</script>

<template>
	<div class="flex flex-1 flex-col overflow-scroll scrollbar-hide">
		<NativeQueryEditor />
		<QueryResult />
	</div>
</template>
