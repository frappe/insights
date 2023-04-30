<template>
	<node-view-wrapper class="not-prose text-base">
		<AsyncQueryBlock
			:query="props.node.attrs.query"
			@setQuery="props.updateAttributes({ query: $event })"
			@remove="props.deleteNode()"
		/>
	</node-view-wrapper>
</template>

<script setup>
import { NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3'
import AsyncQueryBlock from '../../../blocks/query/AsyncQueryBlock.vue'
const props = defineProps(nodeViewProps)
</script>
