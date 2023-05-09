<script setup>
import { inject } from 'vue'

const state = inject('state')
</script>

<template>
	<div class="flex h-9 items-center justify-between rounded-t-lg px-3 text-base">
		<div class="flex items-center space-x-2">
			<p class="font-code text-gray-500">{{ state.query.doc.name }}</p>
			<LoadingIndicator v-if="state.query.loading" class="w-3.5 text-gray-300" />
		</div>
	</div>
</template>
