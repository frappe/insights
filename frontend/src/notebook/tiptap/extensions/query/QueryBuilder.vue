<template>
	<node-view-wrapper class="not-prose text-base">
		<AsyncComponent>
			<QueryBlock
				:query="props.node.attrs.name"
				:is_native="props.node.attrs.is_native"
				@setQuery="props.updateAttributes({ name: $event })"
				@remove="props.deleteNode()"
			/>
		</AsyncComponent>
	</node-view-wrapper>
</template>

<script setup>
import AsyncComponent from '@/components/AsyncComponent.vue'
import QueryBlock from '@/notebook/blocks/query/QueryBlock.vue'
import { NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3'
const props = defineProps(nodeViewProps)
</script>
