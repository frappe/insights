<script setup>
import { inject } from 'vue'
import ResizeableInput from './builder/ResizeableInput.vue'

const state = inject('state')
</script>

<template>
	<div class="flex h-9 items-center justify-between rounded-t-lg px-3 text-base">
		<div class="font-code flex items-center">
			<ResizeableInput v-model="state.query.doc.title" class="-ml-2"></ResizeableInput>
			<p class="text-gray-500">({{ state.query.doc.name }})</p>
			<p
				class="ml-2.5 h-1.5 w-1.5 rounded-full"
				:class="[!state.query.unsaved ? 'hidden' : 'bg-orange-500']"
			></p>
		</div>
	</div>
</template>
