<template>
	<SwitchGroup v-bind="$attrs">
		<div class="flex items-center justify-between text-sm">
			<SwitchLabel v-if="$props.label" class="mr-4 select-none text-xs text-gray-600">
				{{ $props.label }}
			</SwitchLabel>
			<Switch
				:modelValue="Boolean(enabled)"
				@update:modelValue="enabled = Boolean($event)"
				class="relative inline-flex items-center rounded-full transition-colors"
				:class="[
					enabled ? 'bg-gray-900' : 'bg-gray-300',
					props.size === 'sm' ? 'h-4 w-6.5' : 'h-4.5 w-8',
				]"
				:disabled="props.disabled"
			>
				<span
					:class="[
						enabled
							? props.size == 'sm'
								? 'translate-x-3'
								: 'translate-x-4'
							: 'translate-x-1',
						props.size == 'sm' ? 'h-2.5 w-2.5' : ' h-3 w-3 ',
					]"
					class="inline-block transform rounded-full bg-white transition-transform"
				/>
			</Switch>
		</div>
	</SwitchGroup>
</template>

<script setup lang="ts">
import { Switch, SwitchGroup, SwitchLabel } from '@headlessui/vue'

const enabled = defineModel<Boolean | Number>()
const props = defineProps<{
	label?: string
	size?: 'sm' | 'md'
	disabled?: boolean
}>()
</script>
