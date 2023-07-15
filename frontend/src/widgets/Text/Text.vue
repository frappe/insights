<script setup>
import { TextEditor } from 'frappe-ui'
import { inject } from 'vue'
const props = defineProps({
	item_id: { required: true },
	options: { type: Object, required: true },
})
const dashboard = inject('dashboard')
</script>

<template>
	<div
		v-if="options.markdown"
		class="relative flex h-full w-full items-center px-2"
		:class="[dashboard.editing ? 'rounded border-2 border-dashed border-gray-300' : '']"
	>
		<TextEditor
			editor-class="h-fit prose-sm flex flex-col justify-end"
			:content="options.markdown"
			:editable="false"
		/>
	</div>
	<template v-else>
		<slot name="placeholder"></slot>
	</template>
</template>

<style lang="scss">
.prose-sm {
	& > h1,
	& > h2,
	& > h3,
	& > h4,
	& > h5,
	& > h6 {
		@apply my-1;
	}
}
</style>
