<script setup lang="ts">
import { inject, ref } from 'vue'
import QueryOperations from './QueryOperations.vue'
// import queryExample from './pipeline_example';
import { Columns2, GanttChartIcon } from 'lucide-vue-next'
import { Query } from './useQuery'

const query = inject('query') as Query

const currentTab = ref('Operations')
const tabs = [
	// { label: 'Data', icon: Columns2 },
	{ label: 'Operations', icon: GanttChartIcon },
]
</script>

<template>
	<div class="flex h-full flex-col">
		<QueryOperations v-if="currentTab === 'Operations'" />
	</div>
</template>
