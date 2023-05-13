<template>
	<div class="group flex items-start space-x-2.5 text-base">
		<div class="w-[10ch] py-1 text-right text-sm uppercase text-gray-500">
			{{ $props.label }}
		</div>
		<slot></slot>
		<div
			v-if="onRemove"
			class="!ml-2 cursor-pointer rounded-lg p-1.5 text-gray-400 opacity-0 transition-opacity hover:text-gray-800 group-hover:opacity-100"
			@click.prevent.stop="onRemove()"
		>
			<FeatherIcon name="x" class="h-4 w-4" />
		</div>
	</div>
</template>

<script setup>
defineProps({ label: String, onRemove: Function })
</script>
