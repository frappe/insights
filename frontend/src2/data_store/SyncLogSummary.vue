<script setup lang="ts">
import { CheckCircle2Icon, XCircleIcon, Circle } from 'lucide-vue-next'
import type { SyncLog } from './data_store'
import { __ } from '../translation'

const props = defineProps<{
	log: SyncLog | null
	syncMode: string
}>()

const statusColors: Record<string, string> = {
	Completed: 'text-green-700',
	Failed: 'text-red-700',
	'In Progress': 'text-blue-700',
}

function formatDuration(seconds: number): string {
	if (seconds < 60) return `${seconds}s`
	const mins = Math.floor(seconds / 60)
	const secs = seconds % 60
	return secs ? `${mins}m ${secs}s` : `${mins}m`
}

function formatNumber(n: number): string {
	return n?.toLocaleString() ?? '0'
}
</script>

<template>
	<div class="border-t bg-gray-50 px-4 py-3 pl-12">
		<div v-if="!log" class="text-sm text-gray-500">
			{{ __('No sync history available') }}
		</div>
		<template v-else>
			<div class="flex items-center gap-4 text-sm">
				<div class="flex items-center gap-1.5">
					<CheckCircle2Icon
						v-if="log.status === 'Completed'"
						class="h-4 w-4 text-green-600"
						stroke-width="1.5"
					/>
					<XCircleIcon
						v-else-if="log.status === 'Failed'"
						class="h-4 w-4 text-red-600"
						stroke-width="1.5"
					/>
					<Circle
						v-else
						class="h-3 w-3 text-blue-400 fill-blue-400 animate-pulse"
						stroke-width="1"
					/>
					<span class="font-medium" :class="statusColors[log.status]">
						{{ log.status }}
					</span>
				</div>

				<span class="text-gray-300">|</span>
				<span class="text-gray-500">{{ syncMode }}</span>

				<template v-if="log.rows_imported">
					<span class="text-gray-300">|</span>
					<span class="text-gray-600">
						{{ formatNumber(log.rows_imported) }} {{ __('rows synced') }}
					</span>
				</template>

				<template v-if="log.time_taken">
					<span class="text-gray-300">|</span>
					<span class="text-gray-500">
						{{ formatDuration(log.time_taken) }}
					</span>
				</template>
			</div>

			<div v-if="log.error" class="mt-2 rounded bg-red-50 p-2 text-xs text-red-700">
				{{ log.error }}
			</div>
		</template>
	</div>
</template>
