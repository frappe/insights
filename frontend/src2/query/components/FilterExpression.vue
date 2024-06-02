<script setup lang="ts">
import Code from '@/components/Controls/Code.vue'
import { expression } from '../helpers'

const filterExpression = defineModel<FilterExpression>({
	default: () => ({ expression: expression('') }),
	required: true,
})
</script>

<template>
	<div class="min-h-[1.75rem] w-full rounded border text-sm">
		<Code
			class="filter-expression"
			v-model="filterExpression.expression.expression"
			language="python"
		/>
	</div>
</template>

<style lang="scss">
.filter-expression {
	.cm-content {
		padding: 0 !important;
	}
}
</style>
