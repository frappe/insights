<script setup>
import useDataSources from '@/datasource/useDataSources'
import { inject } from 'vue'

const state = inject('state')
const sources = useDataSources()
sources.reload()
</script>

<template>
	<div
		class="flex h-9 items-center justify-between rounded-t-lg px-3 text-base"
		@mouseover="state.showQueryActions = true"
		@mouseleave="state.showQueryActions = false"
	>
		<div class="flex items-center space-x-2">
			<p class="font-code text-gray-500">{{ state.query.doc.name }}</p>
			<LoadingIndicator v-if="state.query.loading" class="w-3.5 text-gray-300" />
		</div>
		<!-- Actions -->
		<div
			class="absolute right-1 top-1 flex items-center space-x-1 text-sm opacity-0 transition-all"
			:class="{ 'opacity-100': state.showQueryActions }"
		>
			<select
				class="flex h-7 w-32 cursor-pointer items-center rounded-md border !border-gray-200 bg-white px-2 py-0 text-sm text-gray-600 !outline-none !ring-0 transition-all hover:bg-gray-50 hover:text-gray-800"
				@change="state.query.doc.data_source = $event.target.value"
			>
				<option
					v-for="source in sources.list"
					:key="source.name"
					:value="source.name"
					:selected="source.name == state.query.doc.data_source"
				>
					{{ source.title }}
				</option>
			</select>

			<Button
				class="flex h-7 cursor-pointer items-center rounded-md !border !border-gray-200 bg-white px-2 !text-sm !text-gray-600 transition-all hover:bg-gray-50 hover:text-gray-800"
				@click="state.query.execute"
				:loading="state.query.executing"
			>
				Execute
			</Button>
			<div
				class="flex h-7 cursor-pointer items-center rounded-md border px-2 text-gray-600 transition-all hover:bg-gray-50 hover:text-gray-800"
				@click="state.minimizeQuery = !state.minimizeQuery"
			>
				<FeatherIcon
					:name="state.minimizeQuery ? 'maximize-2' : 'minimize-2'"
					class="h-3.5 w-3.5"
				></FeatherIcon>
			</div>
			<Button
				class="flex h-7 cursor-pointer items-center rounded-md !border !border-gray-200 bg-white !px-2 !text-sm !text-gray-600 transition-all hover:bg-gray-50 hover:text-gray-800"
				@click="state.removeQuery"
				:loading="state.query.deleting"
			>
				<FeatherIcon name="trash" class="h-3.5 w-3.5"></FeatherIcon>
			</Button>
		</div>
	</div>
</template>
