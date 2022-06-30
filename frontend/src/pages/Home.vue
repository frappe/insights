<template>
	<div>
		<header class="flex h-20 items-center border-b py-4">
			<h1 class="text-3xl font-bold leading-tight text-gray-900">Home</h1>
		</header>
		<main class="flex h-[calc(100%-5rem)] py-4">
			<div class="grid w-full auto-rows-min grid-cols-3 gap-4">
				<router-link
					v-for="card in cards"
					:key="card.label"
					:to="card.route"
					class="cursor-pointer rounded-md border border-gray-100 px-4 py-6 shadow"
				>
					{{ card.label }}
				</router-link>
			</div>
		</main>
	</div>
</template>

<script setup>
import { ref } from 'vue'

const cards = ref([
	{
		label: 'Data Source',
		route: '/data-source',
	},
	{
		label: 'Table',
		route: '/table',
	},
	{
		label: 'Query',
		route: '/query',
	},
	{
		label: 'Dashboard',
		route: '/dashboard',
	},
])
</script>
