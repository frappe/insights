<script setup>
import Checkbox from '@/components/Controls/Checkbox.vue'
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
		<Input
			type="text"
			label="Title"
			class="w-full"
			v-model="options.title"
			placeholder="Title"
		/>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Progress</span>
			<Autocomplete v-model.value="options.progress" :options="valueOptions" />
		</div>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Target</span>
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
							v-model.value="options.target"
							placeholder="Select a column..."
							:options="valueOptions"
						/>
						<Input
							v-if="options.targetType === 'Value'"
							v-model="options.target"
							placeholder="Enter a value..."
							type="number"
							class="h-8"
						/>
					</div>
				</template>
			</InputWithTabs>
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
		<Checkbox v-model="options.shorten" label="Shorten Numbers" />
	</div>
</template>
