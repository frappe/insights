<script setup lang="ts">
import Code from '../../components/Code.vue'
import { Expression } from '../../types/query.types'
import { expression } from '../helpers'

const props = defineProps<{ placeholder?: string }>()
const modelValue = defineModel<Expression>({
	default: () => expression(''),
	required: true,
})
</script>

<template>
	<div class="min-h-[1.75rem] w-full rounded border text-sm">
		<Code
			class="inline-expression"
			v-model="modelValue.expression"
			language="python"
			:placeholder="placeholder"
		/>
	</div>
</template>
