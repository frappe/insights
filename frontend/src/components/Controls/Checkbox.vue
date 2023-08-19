<template>
	<SwitchGroup v-bind="$attrs">
		<div class="flex items-center justify-between">
			<SwitchLabel class="mr-4 text-gray-600">{{ $props.label }}</SwitchLabel>
			<Switch
				v-model="enabled"
				:class="enabled ? 'bg-blue-600' : 'bg-gray-200'"
				class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors"
			>
				<span
					:class="enabled ? 'translate-x-5' : 'translate-x-1'"
					class="inline-block h-3 w-3 transform rounded-full bg-white transition-transform"
				/>
			</Switch>
		</div>
	</SwitchGroup>
</template>

<script setup>
import { computed } from 'vue'
import { Switch, SwitchGroup, SwitchLabel } from '@headlessui/vue'

const props = defineProps(['modelValue', 'label'])
const emits = defineEmits(['update:modelValue'])

const enabled = computed({
	get: () => props.modelValue,
	set: (value) => emits('update:modelValue', value),
})
</script>
