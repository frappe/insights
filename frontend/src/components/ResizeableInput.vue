<script setup>
import ContentEditable from './ContentEditable.vue'
import { computed } from 'vue'
const emit = defineEmits(['update:modelValue'])
const props = defineProps({ modelValue: String | Number, placeholder: String })
const value = computed({
	get: () => props.modelValue || '',
	set: (value) => emit('update:modelValue', value),
})
</script>

<template>
	<ContentEditable
		v-model="value"
		:placeholder="props.placeholder"
		class="h-7 cursor-pointer px-2.5 leading-7 outline-none ring-0 transition-all focus:outline-none"
		:class="$attrs.class"
	/>
</template>
