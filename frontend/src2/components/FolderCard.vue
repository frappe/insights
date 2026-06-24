<script setup lang="ts">
import { Folder } from 'lucide-vue-next'
import { __ } from '../translation'

defineProps<{ title: string }>()
const emit = defineEmits<{ open: [] }>()
</script>

<template>
	<div
		class="group relative flex w-full cursor-pointer flex-col gap-2 rounded bg-white"
		@click="emit('open')"
	>
		<div
			class="flex h-[150px] items-center justify-center overflow-hidden rounded bg-gray-50/70 shadow transition-transform duration-200 group-hover:scale-[1.01]"
		>
			<Folder class="h-12 w-12 text-gray-400" stroke-width="1.25" />
		</div>

		<div class="flex items-center justify-between gap-2">
			<div class="min-w-0 flex-1">
				<p class="truncate text-sm" :title="title">{{ title }}</p>
				<div class="mt-1.5 flex gap-2">
					<span class="text-xs text-gray-600">{{ __('Folder') }}</span>
				</div>
			</div>
		</div>
	</div>
</template>
