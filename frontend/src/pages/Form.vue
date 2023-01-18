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
</script>

<template>
	<div class="flex flex-col space-y-3">
		<Input
			v-for="field in meta.fields"
			:key="field.name"
			:type="field.type"
			:label="field.label"
			:options="field.options"
			:placeholder="field.placeholder"
			v-model="modelValue[field.name]"
		/>
	</div>
</template>
