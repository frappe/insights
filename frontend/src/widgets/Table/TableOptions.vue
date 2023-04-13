<script setup>
import Checkbox from '@/components/Controls/Checkbox.vue'
import ListPicker from '@/components/Controls/ListPicker.vue'
import { useQuery } from '@/query/useQueries'
import { computed, ref, watch } from 'vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	modelValue: { type: Object, required: true },
})

const options = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})

const query = ref(useQuery(options.value.query))
// prettier-ignore
watch(() => options.value.query, (queryName) => {
	query.value = useQuery(queryName)
})

const columnOptions = computed(() => {
	return query.value?.resultColumns?.map((column) => ({
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
			<span class="mb-2 block text-sm leading-4 text-gray-700">Columns</span>
			<ListPicker
				:options="columnOptions"
				:value="options.columns"
				@change="options.columns = $event.map((item) => item.value)"
			/>
		</div>
		<Checkbox v-model="options.index" label="Show Index" />
		<Checkbox v-model="options.showTotal" label="Show Total" />
	</div>
</template>
