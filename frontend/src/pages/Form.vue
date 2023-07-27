<script setup>
import { computed } from 'vue'
const props = defineProps({
	meta: {
		type: Object,
		required: true,
	},
	modelValue: {
		type: Object,
		required: true,
	},
})

const modelValue = computed({
	get: () => props.modelValue,
	set: (value) => {
		emit('update:modelValue', value)
	},
})
props.meta.fields.forEach((field) => {
	if (field.defaultValue) {
		modelValue.value[field.name] = field.defaultValue
	}
})
</script>

<template>
	<div class="flex flex-col space-y-4">
		<div class="relative" v-for="field in meta.fields" :key="field.name">
			<Input
				:type="field.type"
				:label="field.label"
				:options="field.options"
				:placeholder="field.placeholder"
				v-model="modelValue[field.name]"
			/>
			<span
				v-if="field.required && !modelValue[field.name]"
				class="absolute right-0 top-1 text-xs text-red-400"
			>
				* required
			</span>
		</div>
	</div>
</template>
