<template>
	<BinaryExpression v-if="type == 'BinaryExpression'" :expression="props.term" />
	<CallExpression v-else-if="type == 'CallExpression'" :expression="props.term" />
	<!-- Column -->
	<p class="w-fit" v-else-if="type == 'Column'">
		<!-- {{ value.table }} -->
		<!-- <span class="text-gray-500">&#8226;</span> -->
		{{ value.column }}
	</p>
	<!-- Number or String -->
	<p class="w-fit" v-else-if="type == 'String'">"{{ value }}"</p>
	<p class="w-fit" v-else-if="type == 'Number'">
		{{ value }}
	</p>
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
