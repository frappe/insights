<script setup>
import { useQuery } from '@/query/useQueries'
import { FIELDTYPES } from '@/utils'
import { computed, ref, watch } from 'vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	modelValue: { type: Object, required: true },
})

const options = computed({
	get() {
		return props.modelValue
	},
	set(value) {
		emit('update:modelValue', value)
	},
})

const query = ref(useQuery(options.value.query))
// prettier-ignore
watch(() => options.value.query, (queryName) => {
	query.value = useQuery(queryName)
})

const columnOptions = computed(() => {
	return query.value?.resultColumns
		?.filter((column) => FIELDTYPES.NUMBER.includes(column.type))
		.map((column) => ({
			label: column.column,
			value: column.column,
			description: column.type,
		}))
})
</script>

<template>
	<div class="space-y-4">
		<Input
			type="text"
			label="Title"
			class="w-full"
			v-model="options.title"
			placeholder="Title"
		/>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Number Column</span>
			<Autocomplete v-model.value="options.column" :options="columnOptions" />
		</div>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Prefix</span>
			<Input type="text" v-model="options.prefix" placeholder="Enter a prefix..." />
		</div>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Suffix</span>
			<Input type="text" v-model="options.suffix" placeholder="Enter a suffix..." />
		</div>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Decimals</span>
			<Input type="number" v-model="options.decimals" placeholder="Enter a number..." />
		</div>
	</div>
</template>
