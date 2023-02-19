<script setup>
import LinkIcon from '@/components/Controls/LinkIcon.vue'
import useQueries from '@/query/useQueries'
import { getQueryLink } from '@/utils'
import { whenever } from '@vueuse/shared'
import { computed, inject } from 'vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps(['modelValue'])
const dashboard = inject('dashboard')

const queryName = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})
const queries = useQueries()
queries.reload()
whenever(queryName, (query) => dashboard.loadQuery(query), { immediate: true })
</script>

<template>
	<div class="space-y-2">
		<span class="mb-2 block text-sm leading-4 text-gray-700">Query</span>
		<LinkIcon :link="getQueryLink(queryName)">
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
		</LinkIcon>
	</div>
</template>
