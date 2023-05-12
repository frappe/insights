<script setup>
import ContentEditable from '@/notebook/ContentEditable.vue'
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
		class="cursor-pointer px-2.5 py-0.5 outline-none ring-0 transition-all focus:outline-none"
	/>
</template>
