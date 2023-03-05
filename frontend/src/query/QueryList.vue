<script setup>
import { onMounted, ref } from 'vue'
import useQueries from './useQueries'
import useSources from './useSources'

const emit = defineEmits(['select'])
const searchText = ref('')
const queries = useQueries()
queries.reload()
const openQuery = (name) => {
	searchText.value = ''
	emit('select', name)
}

const sources = useSources()
sources.reload()

const createStep = ref(false)
const newSource = ref('')
const createNewQuery = async (source) => {
	newSource.value = source
	const name = await queries.create(source)
	newSource.value = ''
	emit('select', name)
}

const searchInput = ref(null)
onMounted(() => searchInput.value.focus())
</script>

<template>
	<div class="min-w-[29rem] overflow-hidden rounded-md border bg-white text-base">
		<template v-if="!createStep">
			<div class="flex items-center border-b px-4">
				<FeatherIcon name="search" class="absolute h-4 w-4 text-gray-500" />
				<input
					ref="searchInput"
					v-model="searchText"
					class="ml-2 flex h-12 w-full items-center rounded-t-md px-4 placeholder:text-gray-400 focus:outline-none"
					placeholder="Search by query title, source, name..."
				/>
			</div>
			<div class="flex h-[15rem] w-full flex-col overflow-y-scroll">
				<div
					class="sticky top-0 flex-shrink-0 bg-white px-3 pt-2 pb-1 text-sm text-gray-500"
				>
					{{ searchText ? 'Search Results' : 'Recent Queries' }}
				</div>
				<div
					v-for="query in queries.filterByText(searchText).slice(0, 50)"
					class="flex h-10 flex-shrink-0 cursor-pointer items-center space-x-2 px-3 hover:bg-gray-100"
					@click="openQuery(query.name)"
				>
					<FeatherIcon name="file" class="h-4 w-4 text-gray-500" />
					<div class="flex w-full items-baseline justify-between">
						<div class="max-w-[15rem] overflow-hidden text-ellipsis whitespace-nowrap">
							{{ query.title }}
						</div>
						<div class="ml-4 flex-shrink-0 text-sm text-gray-500">
							{{ query.name }}
							<span class="text-gray-400">&#8226;</span>
							{{ query.data_source }}
						</div>
					</div>
				</div>

				<div
					v-if="!queries.filterByText(searchText).length"
					class="flex h-10 cursor-pointer items-center justify-center text-center text-sm text-gray-400"
				>
					No results found
				</div>
			</div>

			<div class="border-t">
				<div
					class="flex h-10 cursor-pointer items-center space-x-2 px-3 text-blue-600 hover:bg-gray-100"
					@click="createStep = true"
				>
					<FeatherIcon name="plus" class="h-4 w-4" />
					<div class="flex w-full items-baseline justify-between">
						<span>Create New Query</span>
					</div>
				</div>
			</div>
		</template>

		<div v-else class="py-2">
			<div class="px-3 pb-1 text-sm text-gray-500">
				Create Query
				<FeatherIcon name="chevron-right" class="inline h-4 w-4 text-gray-500" />
				Select a Source
			</div>

			<div
				v-for="source in sources.list"
				class="flex h-10 cursor-pointer items-center space-x-2 px-3 hover:bg-gray-100"
				@click="createNewQuery(source.name)"
			>
				<FeatherIcon name="database" class="h-4 w-4 text-gray-500" />
				<div class="flex w-full items-baseline justify-between">
					<span>{{ source.name }}</span>
				</div>
				<LoadingIndicator
					v-if="newSource == source.name && queries.creating"
					class="mr-2 -ml-1 h-3 w-3"
				/>
			</div>
		</div>
	</div>
</template>
