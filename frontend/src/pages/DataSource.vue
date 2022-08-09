<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1 justify-between">
				<h1 v-if="dataSource" class="text-3xl font-medium text-gray-900">
					{{ dataSource.title }}
				</h1>
			</div>
		</template>
		<template #main> </template>
	</BasePage>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'
import { reactive } from 'vue'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
})

const dataSource = reactive({
	title: props.name,
})
</script>
