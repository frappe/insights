<script setup>
import DashboardQueryDialog from '@/dashboard/DashboardQueryDialog.vue'
import CreateQueryDialog from '@/dashboard/CreateQueryDialog.vue'
import useQueries from '@/query/useQueries'
import { computed, ref } from 'vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps(['modelValue'])

const queryName = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})
const queries = useQueries()
queries.reload()

const showCreateQueryDialog = ref(false)
const showQueryBuilder = ref(false)

function openQuery(name) {
	queryName.value = name
	showCreateQueryDialog.value = false
	showQueryBuilder.value = true
}
</script>

<template>
	<div class="space-y-2">
		<span class="mb-2 block text-sm leading-4 text-gray-700">Query</span>
		<div class="relative">
			<Autocomplete
				v-model.value="queryName"
				placeholder="Select a query"
				:allow-create="true"
				@create-option="showCreateQueryDialog = true"
				:options="
					queries.list.map((query) => ({
						label: query.title,
						value: query.name,
					}))
				"
			/>
			<div
				v-if="queryName"
				class="absolute top-0 right-0 flex h-full w-8 cursor-pointer items-center justify-center"
				@click="showQueryBuilder = true"
			>
				<FeatherIcon
					name="maximize-2"
					class="h-3.5 w-3.5 text-gray-600 hover:text-gray-900"
				/>
			</div>
		</div>
	</div>

	<CreateQueryDialog v-model:show="showCreateQueryDialog" @create="openQuery" />
	<DashboardQueryDialog
		v-if="queryName"
		v-model:show="showQueryBuilder"
		:query="queryName"
		@close="queries.reload"
	/>
</template>
