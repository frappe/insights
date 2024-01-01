<template>
	<node-view-wrapper class="not-prose text-base">
		<Suspense>
			<QueryBlock
				:query="props.node.attrs.query"
				@setQuery="props.updateAttributes({ query: $event })"
				@remove="props.deleteNode()"
			/>
		</Suspense>
	</node-view-wrapper>
</template>

<script setup>
import QueryBlock from '@/notebook/blocks/query/QueryBlock.vue'
import { NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3'
const props = defineProps(nodeViewProps)
</script>
