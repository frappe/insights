<template>
	<div class="group flex items-start text-base">
		<div
			v-if="$props.label"
			class="flex h-7 w-[10ch] flex-shrink-0 justify-end text-right text-sm uppercase leading-7 text-gray-600"
		>
			{{ $props.label }}
		</div>
		<div class="ml-2.5 flex flex-wrap gap-y-4 gap-x-2.5">
			<slot></slot>

			<div class="!-ml-1">
				<Button
					v-for="action in actions"
					:icon="action.icon"
					variant="ghost"
					class="!text-gray-600"
					@click.prevent.stop="action.onClick"
				>
				</Button>
			</div>
		</div>
	</div>
</template>

<script setup>
defineProps({ label: String, actions: Array })
</script>
