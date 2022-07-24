<template>
	<BinaryExpression v-if="type == 'BinaryExpression'" :expression="props.term" />
	<CallExpression v-else-if="type == 'CallExpression'" :expression="props.term" />
	<!-- Column -->
	<div v-else-if="type == 'Column'">{{ value.table }}.{{ value.column }}</div>
	<!-- Number or String -->
	<div v-else-if="type == 'String'">{{ value }}</div>
	<div v-else-if="type == 'Number'">{{ value }}</div>
</template>

<script setup>
import BinaryExpression from '@/components/Query/Filter/BinaryExpression.vue'
import CallExpression from '@/components/Query/Filter/CallExpression.vue'

const props = defineProps({
	term: {
		type: Object,
		required: true,
	},
})
const type = props.term.type
const value = props.term.value
</script>
