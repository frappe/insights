<script setup lang="ts">
import QueryBuilder from '@/query/next/QueryBuilder.vue'
import Footer from './components/Footer.vue'
import Header from './components/Header.vue'
</script>

<template>
	<div class="flex h-full flex-col">
		<Header />
		<QueryBuilder />
		<Footer />
	</div>
</template>
