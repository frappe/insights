<script setup lang="ts">
defineOptions({ inheritAttrs: false })
const props = defineProps<{ label: string }>()
</script>

<template>
	<div class="flex items-start justify-between gap-1">
		<span
			class="inline-flex w-[30%] flex-shrink-0 text-xs leading-7 text-ink-gray-5"
			:class="$attrs.class"
		>
			{{ props.label }}
		</span>
		<div class="h-full min-w-0 flex-1 overflow-hidden">
			<slot />
		</div>
	</div>
</template>
