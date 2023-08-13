<script setup>
import { inject } from 'vue'
import ResizeableInput from './builder/ResizeableInput.vue'

const state = inject('state')
const debouncedUpdateTitle = debounce(async (title) => {
	await state.query.setValue.submit({ title })
	query.doc.title = title
}, 1500)
</script>

<template>
	<div class="flex h-9 items-center justify-between rounded-t-lg px-3 text-base">
		<div class="flex items-center font-mono">
			<ResizeableInput
				v-model="state.query.doc.title"
				class="-ml-2 cursor-text"
				@update:model-value="debouncedUpdateTitle"
			></ResizeableInput>
			<p class="text-gray-600">({{ state.query.doc.name }})</p>
			<p
				class="ml-2.5 h-1.5 w-1.5 rounded-full"
				:class="[!state.query.unsaved ? 'hidden' : 'bg-orange-500']"
			></p>
		</div>
	</div>
</template>
