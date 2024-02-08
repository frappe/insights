<template>
	<Button variant="ghost" @click="show = true" icon="help-circle"> </Button>

	<Dialog :options="{ title: 'Functions' }" v-model="show" :dismissable="true">
		<template #body-content>
			<input
				v-model="search"
				placeholder="Search functions"
				class="form-input block w-full border-gray-400 placeholder-gray-500"
			/>
			<div
				class="mt-4 flex max-h-[30rem] flex-col space-y-1 divide-y overflow-y-auto text-base"
			>
				<div v-for="func in filteredList" :key="func.name" class="flex">
					<div class="flex-1 space-y-1 py-2">
						<p class="font-mono text-lg font-medium">{{ func.name }}</p>
						<p class="text-sm text-gray-600">{{ func.description }}</p>
					</div>
					<div class="mt-2 flex-1 rounded bg-gray-50 p-2 text-sm leading-5">
						<code>
							<span class="text-gray-600"># Syntax</span>
							<br />
							{{ func.syntax }}
							<br />
							<br />
							<span class="text-gray-600"># Example</span>
							<br />
							{{ func.example }}
						</code>
					</div>
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
