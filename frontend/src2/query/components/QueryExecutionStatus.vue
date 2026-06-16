<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'
import { inject } from 'vue'
import { __ } from '../../translation'
import { Query } from '../query'

const query = inject('query') as Query
</script>

<template>
	<div
		v-show="query.result.executedSQL"
		class="tnum flex flex-shrink-0 items-center gap-2 text-sm text-gray-600"
	>
		<div class="h-2 w-2 rounded-full bg-green-500"></div>
		<div class="flex items-center gap-1">
			<span v-if="query.result.timeTaken == -1">
				{{ __('Fetched from cache') }}
			</span>
			<span v-else>
				{{ __('Fetched in {0}s', String(query.result.timeTaken)) }}
			</span>
			<span> {{ useTimeAgo(query.result.lastExecutedAt).value }} </span>
		</div>
	</div>
</template>
