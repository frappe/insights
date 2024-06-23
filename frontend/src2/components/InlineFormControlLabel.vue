<script setup lang="ts">
defineOptions({ inheritAttrs: false })
const props = defineProps<{ label: string }>()
</script>

<template>
	<div class="flex items-center justify-between gap-1">
		<span
			class="inline-flex w-1/3 flex-shrink-0 text-xs leading-5 text-gray-700"
			:class="$attrs.class"
		>
			{{ props.label }}
		</span>
		<div class="flex-1 overflow-hidden">
			<slot />
		</div>
	</div>
</template>
