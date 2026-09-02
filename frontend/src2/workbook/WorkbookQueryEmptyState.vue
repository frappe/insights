<script setup lang="ts">
import { Braces, ScrollText, SquareMousePointer } from 'lucide-vue-next'

const emit = defineEmits({
	select: (interfaceType: 'query-builder' | 'sql-editor' | 'script-editor') => true,
})
</script>

<template>
	<div class="flex h-full w-full items-center justify-center bg-surface-gray-1">
		<div class="flex flex-col space-y-4">
			<div class="text-center text-ink-gray-4">Select an interface to start</div>
			<div
				class="flex w-full cursor-pointer items-center gap-4 rounded-4 border border-transparent bg-surface-base p-2 shadow-sm transition-all hover:border-outline-gray-2"
				@click="emit('select', 'query-builder')"
			>
				<div class="w-fit rounded-4 bg-surface-blue-1 p-3">
					<SquareMousePointer class="h-5 w-5 text-ink-blue-5/70" stroke-width="1.5" />
				</div>
				<div class="flex flex-col gap-1">
					<p class="font-medium text-ink-gray-6">Query Builder</p>
					<p class="text-sm text-ink-gray-4">Create queries with a visual interface</p>
				</div>
			</div>
			<div
				class="flex w-full cursor-pointer items-center gap-4 rounded-4 border border-transparent bg-surface-base p-2 shadow-sm transition-all hover:border-outline-gray-2"
				@click="emit('select', 'sql-editor')"
			>
				<div class="w-fit rounded-4 bg-surface-orange-1 p-3">
					<ScrollText class="h-5 w-5 text-ink-orange-5/70" stroke-width="1.5" />
				</div>
				<div class="flex flex-col gap-1">
					<p class="font-medium text-ink-gray-6">SQL Editor</p>
					<p class="text-sm text-ink-gray-4">Create queries with raw SQL</p>
				</div>
			</div>
			<div
				class="flex w-full cursor-pointer items-center gap-4 rounded-4 border border-transparent bg-surface-base p-2 shadow-sm transition-all hover:border-outline-gray-2"
				@click="emit('select', 'script-editor')"
			>
				<div class="w-fit rounded-4 bg-surface-green-1 p-3">
					<Braces class="h-5 w-5 text-ink-green-5/70" stroke-width="1.5" />
				</div>
				<div class="flex flex-col gap-1">
					<p class="font-medium text-ink-gray-6">Script Editor</p>
					<p class="text-sm text-ink-gray-4">Create queries with a python script</p>
				</div>
			</div>
		</div>
	</div>
</template>
