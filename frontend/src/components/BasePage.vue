<template>
	<div class="h-full">
		<div class="flex h-14 bg-white shadow">
			<NavBar />
		</div>
		<div
			class="mx-auto flex h-[calc(100%-3.5rem)] w-full max-w-[85rem] flex-col px-4 py-4 sm:px-6 lg:px-8"
		>
			<header class="flex h-20 items-center pb-4">
				<slot name="header" />
			</header>
			<main class="flex h-[calc(100%-5rem)]">
				<slot name="main" />
			</main>
		</div>
	</div>
</template>

<script setup>
import NavBar from '@/components/NavBar.vue'
</script>
