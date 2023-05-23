<script setup>
import useQueries from '@/query/useQueries'
import { computed } from 'vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps(['modelValue'])

const queryName = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})
const queries = useQueries()
queries.reload()

function openQueryInNewTab() {
	window.open(`/insights/query/build/${queryName.value}`, '_blank')
}
</script>

<template>
	<div class="space-y-2">
		<span class="mb-2 block text-sm leading-4 text-gray-700">Query</span>
		<div class="relative">
			<Autocomplete
				v-model.value="queryName"
				placeholder="Select a query"
				:options="
					queries.list.map((query) => ({
						label: query.title,
						value: query.name,
					}))
				"
			/>
			<div
				v-if="queryName"
				class="absolute right-0 top-0 flex h-full w-8 cursor-pointer items-center justify-center"
				@click="openQueryInNewTab"
			>
				<FeatherIcon
					name="maximize-2"
					class="h-3.5 w-3.5 text-gray-600 hover:text-gray-900"
				/>
			</div>
		</div>
	</div>
</template>
