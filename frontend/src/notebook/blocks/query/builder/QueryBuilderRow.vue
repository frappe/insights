<template>
	<div class="group flex items-start space-x-2.5 text-base">
		<div
			v-if="$props.label"
			class="flex h-7 w-[10ch] flex-shrink-0 justify-end text-sm uppercase leading-7 text-gray-600"
		>
			{{ $props.label }}
		</div>
		<slot></slot>
		<Button
			v-if="onRemove"
			icon="x"
			variant="ghost"
			class="!text-gray-600"
			@click.prevent.stop="onRemove()"
		>
		</Button>
	</div>
</template>

<script setup>
defineProps({ label: String, onRemove: Function })
</script>
