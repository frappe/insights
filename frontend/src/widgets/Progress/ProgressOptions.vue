<script setup>
import InputWithTabs from '@/components/Controls/InputWithTabs.vue'
import { FIELDTYPES } from '@/utils'
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

const valueOptions = computed(() => {
	return props.columns
		?.filter((column) => FIELDTYPES.NUMBER.includes(column.type))
		.map((column) => ({
			label: column.label,
			value: column.label,
			description: column.type,
		}))
})

if (!options.value.targetType) {
	options.value.targetType = 'Column'
}
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
			<label class="mb-1.5 block text-xs text-gray-600">Progress Column</label>
			<Autocomplete v-model="options.progress" :returnValue="true" :options="valueOptions" />
		</div>
		<div>
			<label class="mb-1.5 block text-xs text-gray-600">Target</label>
			<InputWithTabs
				:value="options.targetType"
				:tabs="{
					Column: options.targetType === 'Column',
					Value: options.targetType === 'Value',
				}"
				@tab-change="options.targetType = $event"
			>
				<template #inputs>
					<div class="w-full">
						<Autocomplete
							v-if="options.targetType === 'Column'"
							v-model="options.target"
							:returnValue="true"
							placeholder="Select a column..."
							:options="valueOptions"
						/>
						<FormControl
							v-if="options.targetType === 'Value'"
							v-model="options.target"
							placeholder="Enter a value..."
							type="number"
						/>
					</div>
				</template>
			</InputWithTabs>
		</div>
		<FormControl
			label="Prefix"
			type="text"
			v-model="options.prefix"
			placeholder="Enter a prefix..."
		/>
		<FormControl
			label="Suffix"
			type="text"
			v-model="options.suffix"
			placeholder="Enter a suffix..."
		/>
		<FormControl
			label="Decimals"
			type="number"
			v-model="options.decimals"
			placeholder="Enter a number..."
		/>
		<Checkbox v-model="options.shorten" label="Shorten Numbers" />
	</div>
</template>
