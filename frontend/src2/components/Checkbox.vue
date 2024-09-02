<template>
	<SwitchGroup v-bind="$attrs">
		<div class="flex items-center justify-between text-sm">
			<SwitchLabel class="mr-4 select-none text-base font-medium text-gray-800">
				{{ $props.label }}
			</SwitchLabel>
			<Switch
				v-model="enabled"
				class="relative inline-flex items-center rounded-full transition-colors"
				:class="[
					enabled ? 'bg-gray-900' : 'bg-gray-300',
					props.size === 'sm' ? 'h-4 w-6' : 'h-4.5 w-8',
				]"
			>
				<span
					:class="[
						enabled
							? props.size == 'sm'
								? 'translate-x-2.5'
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

<script setup>
import { Switch, SwitchGroup, SwitchLabel } from '@headlessui/vue'

const props = defineProps(['label', 'size'])
const enabled = defineModel({ type: Boolean })
</script>
