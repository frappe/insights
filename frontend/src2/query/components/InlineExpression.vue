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

<style lang="scss">
.inline-expression {
	.cm-content {
		padding: 0 !important;
		line-height: 26px !important;
	}
	.cm-placeholder {
		line-height: 26px !important;
	}
	.cm-gutters {
		line-height: 26px !important;
	}
}
</style>
