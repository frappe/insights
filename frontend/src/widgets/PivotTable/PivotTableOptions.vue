<script setup>
import { X } from 'lucide-vue-next'
import { computed } from 'vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	modelValue: { type: Object, required: true },
	columns: { type: Array, required: true },
})

const options = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})
if (!options.value.rows) options.value.rows = []
if (!options.value.columns) options.value.columns = []
if (!options.value.values) options.value.values = []

const columnOptions = computed(() => {
	return props.columns?.map((column) => ({
		label: column.label,
		value: column.label,
		description: column.type,
	}))
})
</script>

<template>
	<div class="space-y-4">
		<FormControl
			type="text"
			label="Title"
			class="w-full"
			v-model="options.title"
			placeholder="Title"
		/>

		<div>
			<div class="mb-1 flex items-center justify-between">
				<div class="flex items-center space-x-1.5">
					<span class="block text-sm leading-4 text-gray-700">Rows</span>
				</div>
				<Autocomplete :multiple="true" v-model="options.rows" :options="columnOptions">
					<template #target="{ togglePopover }">
						<Button variant="ghost" icon="plus" @click="togglePopover"></Button>
					</template>
				</Autocomplete>
			</div>

			<div
				v-for="(row, idx) in options.rows"
				:key="idx"
				class="group form-input flex h-7 cursor-pointer items-center justify-between px-2"
			>
				<div class="flex items-center space-x-2">
					<div>{{ row.label }}</div>
				</div>
				<div class="flex items-center space-x-2">
					<X
						class="invisible h-4 w-4 text-gray-600 transition-all hover:text-gray-800 group-hover:visible"
					/>
				</div>
			</div>
		</div>

		<div>
			<div class="mb-1 flex items-center justify-between">
				<div class="flex items-center space-x-1.5">
					<span class="block text-sm leading-4 text-gray-700">Columns</span>
				</div>
				<Autocomplete :multiple="true" v-model="options.columns" :options="columnOptions">
					<template #target="{ togglePopover }">
						<Button variant="ghost" icon="plus" @click="togglePopover"></Button>
					</template>
				</Autocomplete>
			</div>

			<div
				v-for="(col, idx) in options.columns"
				:key="idx"
				class="group form-input flex h-7 cursor-pointer items-center justify-between px-2"
			>
				<div class="flex items-center space-x-2">
					<div>{{ col.label }}</div>
				</div>
				<div class="flex items-center space-x-2">
					<X
						class="invisible h-4 w-4 text-gray-600 transition-all hover:text-gray-800 group-hover:visible"
					/>
				</div>
			</div>
		</div>

		<div>
			<div class="mb-1 flex items-center justify-between">
				<span class="block text-sm leading-4 text-gray-700">Values</span>
				<Autocomplete :multiple="true" v-model="options.values" :options="columnOptions">
					<template #target="{ togglePopover }">
						<Button variant="ghost" icon="plus" @click="togglePopover"></Button>
					</template>
				</Autocomplete>
			</div>

			<div
				v-for="(val, idx) in options.values"
				:key="idx"
				class="group form-input mb-2 flex h-7 cursor-pointer items-center justify-between px-2"
			>
				<div class="flex items-center space-x-2">
					<div>{{ val.label }}</div>
				</div>
				<div class="flex items-center space-x-2">
					<X
						class="invisible h-4 w-4 text-gray-600 transition-all hover:text-gray-800 group-hover:visible"
					/>
				</div>
			</div>
		</div>
	</div>
</template>
