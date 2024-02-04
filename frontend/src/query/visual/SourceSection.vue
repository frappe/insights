<script setup>
import { DatabaseIcon } from 'lucide-vue-next'
import QueryDataSourceSelector from '../QueryDataSourceSelector.vue'
import SectionHeader from './SectionHeader.vue'
</script>

<template>
	<SectionHeader
		:icon="DatabaseIcon"
		title="Data Source"
		info="Select the data source you want to query."
	>
		<QueryDataSourceSelector></QueryDataSourceSelector>
	</SectionHeader>
</template>
