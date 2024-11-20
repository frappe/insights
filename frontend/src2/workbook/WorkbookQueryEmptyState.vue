<script setup lang="ts">
import { Braces, ScrollText, SquareMousePointer } from 'lucide-vue-next'

const emit = defineEmits({
	select: (interfaceType: 'query-builder' | 'sql-editor' | 'script-editor') => true,
})
</script>

<template>
	<div class="flex h-full w-full items-center justify-center bg-gray-50">
		<div class="flex flex-col space-y-4">
			<div class="text-center text-gray-500">Select an inteface to start</div>
			<div
				class="flex w-full cursor-pointer items-center gap-4 rounded border border-transparent bg-white p-2 shadow-sm transition-all hover:border-gray-300"
				@click="emit('select', 'query-builder')"
			>
				<div class="w-fit rounded bg-blue-50 p-3">
					<SquareMousePointer class="h-5 w-5 text-blue-500/70" stroke-width="1.5" />
				</div>
				<div class="flex flex-col gap-1">
					<p class="font-medium text-gray-700">Query Builder</p>
					<p class="text-sm text-gray-500">Create queries with a visual interface</p>
				</div>
			</div>
			<div
				class="flex w-full cursor-pointer items-center gap-4 rounded border border-transparent bg-white p-2 shadow-sm transition-all hover:border-gray-300"
				@click="emit('select', 'sql-editor')"
			>
				<div class="w-fit rounded bg-orange-50 p-3">
					<ScrollText class="h-5 w-5 text-orange-500/70" stroke-width="1.5" />
				</div>
				<div class="flex flex-col gap-1">
					<p class="font-medium text-gray-700">SQL Editor</p>
					<p class="text-sm text-gray-500">Create queries with raw SQL</p>
				</div>
			</div>
			<div
				class="flex w-full cursor-pointer items-center gap-4 rounded border border-transparent bg-white p-2 shadow-sm transition-all hover:border-gray-300"
				@click="emit('select', 'script-editor')"
			>
				<div class="w-fit rounded bg-green-50 p-3">
					<Braces class="h-5 w-5 text-green-500/70" stroke-width="1.5" />
				</div>
				<div class="flex flex-col gap-1">
					<p class="font-medium text-gray-700">Script Editor</p>
					<p class="text-sm text-gray-500">Create queries with a python script</p>
				</div>
			</div>
		</div>
	</div>
</template>
