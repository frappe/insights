<template>
	<div
		class="absolute bottom-2 left-2 cursor-pointer rounded-full bg-white p-1 text-gray-600 shadow-md transition-all hover:bg-gray-100"
		@click="show = true"
	>
		<FeatherIcon name="help-circle" class="h-4 w-4 cursor-pointer" />
	</div>

	<Dialog :options="{ title: 'Functions' }" v-model="show" :dismissable="true">
		<template #body-content>
			<input
				v-model="search"
				placeholder="Search functions"
				class="form-input block w-full border-gray-400 border-gray-400 placeholder-gray-500"
			/>
			<div
				class="mt-4 flex max-h-[30rem] flex-col space-y-1 divide-y overflow-y-scroll text-base"
			>
				<div v-for="func in filteredList" :key="func.name" class="py-1">
					<span class="text-lg font-medium">{{ func.name }}</span> -
					<span class="text-gray-600">{{ func.syntax }}</span>
					<div class="">{{ func.description }}</div>
					<div class="text-gray-600">{{ func.example }}</div>
				</div>
				<div v-if="!filteredList.length" class="py-2 text-center text-gray-700">
					No functions found
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { FUNCTIONS } from '@/utils/query'
import { computed, ref } from 'vue'

const show = ref(false)
const search = ref('')
const functionsList = Object.keys(FUNCTIONS).map((key) => {
	return {
		name: key,
		...FUNCTIONS[key],
	}
})

const filteredList = computed(() => {
	if (!search.value) return functionsList
	return functionsList.filter((func) => {
		return (
			func.name.toLowerCase().includes(search.value.toLowerCase()) ||
			func.syntax?.toLowerCase().includes(search.value.toLowerCase())
		)
	})
})
</script>
