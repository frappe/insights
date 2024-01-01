<template>
	<div class="h-full w-full pt-4 sm:pt-16">
		<div class="relative z-10">
			<div class="flex">
				<img src="../assets/insights-logo-new.svg" class="mx-auto h-12" />
			</div>
			<div
				class="mx-auto bg-white px-4 py-8 sm:mt-6 sm:w-96 sm:rounded-lg sm:px-8 sm:shadow-xl"
			>
				<div class="mb-6 text-center">
					<span class="text-base text-gray-900">{{ props.title }}</span>
				</div>
				<slot></slot>
			</div>
		</div>
		<div class="fixed bottom-4 z-[1] flex w-full justify-center">
			<FrappeLogo class="h-4" />
		</div>
	</div>
</template>

<script setup>
import FrappeLogo from './Icons/FrappeLogo.vue'
const props = defineProps(['title'])
</script>
