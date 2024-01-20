<script setup>
import Query from '@/query/Query.vue'
import useQueryStore from '@/stores/queryStore'
import { computed, ref } from 'vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps(['modelValue'])

const queryName = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})
const queryStore = useQueryStore()

const queryOptions = computed(() =>
	queryStore.list.map((query) => ({
		label: query.title,
		value: query.name,
	}))
)

function openQueryInNewTab() {
	window.open(`/insights/query/build/${queryName.value}`, '_blank')
}

const showCreateQuery = ref(false)
const newQuery = ref(null)
async function createQuery() {
	newQuery.value = await queryStore.create({ is_assisted_query: 1 })
	showCreateQuery.value = true
}
async function deleteQuery() {
	await queryStore.delete(newQuery.value.name)
	showCreateQuery.value = false
	newQuery.value = null
}
async function selectQuery() {
	await queryStore.reload()
	emit('update:modelValue', newQuery.value.name)
	showCreateQuery.value = false
	newQuery.value = null
}
</script>

<template>
	<div class="space-y-2">
		<span class="mb-2 block text-sm leading-4 text-gray-700">Query</span>
		<div class="relative">
			<Autocomplete
				v-model="queryName"
				:returnValue="true"
				placeholder="Select a query"
				:allowCreate="true"
				:options="queryOptions"
				@createOption="createQuery"
			/>
			<div
				v-if="queryName"
				class="absolute right-0 top-0 flex h-full w-8 cursor-pointer items-center justify-center rounded bg-gray-100"
				@click="openQueryInNewTab"
			>
				<FeatherIcon
					name="maximize-2"
					class="h-3.5 w-3.5 text-gray-600 hover:text-gray-900"
				/>
			</div>
		</div>
	</div>

	<Dialog v-model="showCreateQuery" :dismissable="false" :options="{ size: '2xl' }">
		<template #body>
			<div v-if="newQuery" class="flex h-[46rem] w-full flex-col justify-end p-4 text-base">
				<Query :name="newQuery.name" :hideTabs="true" />
				<div class="ml-auto space-x-2 px-2">
					<Button
						variant="solid"
						theme="red"
						@click="deleteQuery"
						:loading="queryStore.deleting"
					>
						Discard
					</Button>
					<Button variant="solid" @click="selectQuery"> Done </Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
