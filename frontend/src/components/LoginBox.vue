<template>
	<div class="h-full pt-4 sm:pt-16">
		<div>
			<div class="flex">
				<FrappeInsights class="mx-auto h-6 w-auto" />
			</div>
			<div
				class="sm:w-0112 mx-auto bg-white px-4 py-8 sm:mt-6 sm:w-96 sm:rounded-lg sm:px-10 sm:shadow-xl"
			>
				<div class="mb-6 text-center">
					<span class="text-lg">{{ props.title }}</span>
				</div>
				<slot></slot>
			</div>
		</div>
	</div>
</template>

<script setup>
import FrappeInsights from '@/components/Icons/FrappeInsights.vue'

const props = defineProps(['title'])
</script>
