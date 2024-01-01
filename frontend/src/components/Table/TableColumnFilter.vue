<script setup>
import { SearchIcon } from 'lucide-vue-next'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({ modelValue: String })
</script>

<template>
	<FormControl
		type="text"
		autocomplete="off"
		:modelValue="modelValue"
		@update:modelValue="emit('update:modelValue', $event)"
	>
		<template #prefix>
			<SearchIcon class="h-3 w-3 text-gray-500" />
		</template>
	</FormControl>
</template>
