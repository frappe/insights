<script setup>
import Query from '@/query/Query.vue'
import QueryHeader from '@/query/QueryHeader.vue'
const props = defineProps(['name'])
</script>

<template>
	<div class="flex w-full flex-col p-2">
		<Query :name="props.name" :hideTabs="true" />
	</div>
</template>
