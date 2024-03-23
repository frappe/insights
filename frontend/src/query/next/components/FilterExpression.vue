<script setup lang="ts">
import Code from '@/components/Controls/Code.vue'
import { watch } from 'vue'
import { FilterExpression } from '../FiltersSelectorDialog.vue'

const filter = defineModel<FilterExpression>({
	default: () => ({
		expression: '',
		isValid: false,
	}),
	required: true,
})
watch(
	() => filter.value.expression,
	() => {
		filter.value.isValid = filter.value.expression.length > 0
	}
)
</script>

<template>
	<div class="min-h-[1.75rem] w-full rounded border text-sm">
		<Code class="filter-expression" v-model="filter.expression" language="python" />
	</div>
</template>

<style lang="scss">
.filter-expression {
	.cm-content {
		padding: 0 !important;
	}
}
</style>
