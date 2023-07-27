<template>
	<div class="flex flex-1 flex-col overflow-hidden bg-white p-5">
		<Breadcrumbs />
		<header class="flex h-10 flex-shrink-0 overflow-visible">
			<slot name="header" />
		</header>
		<main class="flex flex-1 overflow-hidden">
			<slot name="main" />
		</main>
	</div>
</template>

<script setup>
import Breadcrumbs from '@/components/Breadcrumbs.vue'
</script>
