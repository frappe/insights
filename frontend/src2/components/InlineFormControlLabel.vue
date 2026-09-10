<script setup lang="ts">
defineOptions({ inheritAttrs: false })

const props = defineProps<{
	label: string
	/**
	 * Sizes the control to what its value needs, and pushes it to the row's
	 * right edge so it ends where the toggles do. Any CSS length. Left out, the
	 * control takes the rest of the row, which is what a free-text field wants.
	 */
	controlWidth?: string
}>()
</script>

<template>
	<div class="flex items-start justify-between gap-1">
		<span
			class="inline-flex w-[30%] flex-shrink-0 items-center gap-1 text-xs leading-7 text-ink-gray-5"
			:class="$attrs.class"
		>
			{{ props.label }}
			<slot name="label-suffix" />
		</span>
		<div
			class="h-full min-w-0"
			:class="props.controlWidth ? 'ml-auto flex-none' : 'flex-1'"
			:style="props.controlWidth ? { width: props.controlWidth } : undefined"
		>
			<slot />
		</div>
	</div>
</template>
