<script setup lang="ts">
import { inject } from 'vue'
import { QueryPipeline } from './useQueryPipeline'

const queryPipeline = inject('queryPipeline') as QueryPipeline
</script>

<template>
	<div v-if="queryPipeline.steps.length" class="flex flex-col p-1"></div>
</template>
