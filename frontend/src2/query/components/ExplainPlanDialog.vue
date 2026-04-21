<script setup lang="ts">
import { inject } from 'vue'
import { copyToClipboard } from '../../helpers'
import { __ } from '../../translation'
import { Query } from '../query'

const showDialog = defineModel()

const query = inject('query') as Query
</script>

<template>
	<Dialog
		v-model="showDialog"
		:options="{ title: __('Query Plan'), size: '3xl' }"
		:dismissable="true"
	>
		<template #body-content>
			<div
				v-if="query.explaining"
				class="flex items-center justify-center py-10 text-gray-500"
			>
				<span>{{
					__(
						'Running {0}…',
						query.explainResult?.is_analyze ? 'EXPLAIN ANALYZE' : 'EXPLAIN',
					)
				}}</span>
			</div>
			<div v-else-if="query.explainResult?.plan" class="relative">
				<div class="max-h-[60vh] overflow-auto rounded border bg-gray-50 p-3">
					<pre class="whitespace-pre font-mono text-xs leading-relaxed text-gray-800">{{
						query.explainResult.plan
					}}</pre>
				</div>
				<Button
					icon="copy"
					variant="outline"
					class="absolute bottom-2 right-2"
					@click="copyToClipboard(query.explainResult.plan)"
				/>
			</div>
			<div v-else class="py-6 text-center text-sm text-gray-500">
				{{ __('No plan available. Execute the query first.') }}
			</div>
		</template>
	</Dialog>
</template>
