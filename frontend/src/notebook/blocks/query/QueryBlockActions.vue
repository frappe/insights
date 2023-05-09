<script setup>
import useDataSources from '@/datasource/useDataSources'
import { inject } from 'vue'

const state = inject('state')
const sources = useDataSources()
sources.reload()
</script>

<template>
	<div class="flex w-28 flex-col space-y-1.5 text-sm transition-all">
		<select
			class="flex h-[30px] cursor-pointer items-center rounded-md border !border-gray-200 bg-white px-2 py-0 text-sm text-gray-600 shadow-sm !outline-none !ring-0 transition-all hover:bg-gray-50 hover:text-gray-800"
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
			class="flex cursor-pointer items-center rounded-md !border !border-gray-200 bg-white px-2 !text-left !text-sm !text-gray-600 shadow-sm transition-all hover:bg-gray-50 hover:text-gray-800"
			@click="state.query.execute"
			:loading="state.query.executing"
			iconLeft="play"
		>
			Execute
		</Button>
		<Button
			class="flex cursor-pointer items-center rounded-md !border !border-gray-200 bg-white px-2 !text-left !text-sm !text-gray-600 shadow-sm transition-all hover:bg-gray-50 hover:text-gray-800"
			:iconLeft="state.minimizeQuery ? 'maximize-2' : 'minimize-2'"
			@click="state.minimizeQuery = !state.minimizeQuery"
		>
			{{ state.minimizeQuery ? 'Maximize' : 'Minimize' }}
		</Button>
		<Button
			class="flex cursor-pointer items-center rounded-md !border !border-gray-200 bg-white !px-2 !text-sm !text-gray-600 shadow-sm transition-all hover:bg-gray-50 hover:text-gray-800"
			@click="state.removeQuery"
			:loading="state.query.deleting"
			iconLeft="trash"
		>
			Delete
		</Button>
	</div>
</template>
