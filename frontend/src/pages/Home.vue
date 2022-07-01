<template>
	<BasePage>
		<template #header>
			<h1 class="text-3xl font-bold leading-tight text-gray-900">Home</h1>
		</template>
		<template #main>
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
		</template>
	</BasePage>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'

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
