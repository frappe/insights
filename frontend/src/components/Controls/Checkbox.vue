<template>
	<SwitchGroup>
		<div class="flex items-center justify-between">
			<SwitchLabel class="mr-4 text-gray-500">{{ $props.label }}</SwitchLabel>
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
import { ref, watchEffect } from 'vue'
import { Switch, SwitchGroup, SwitchLabel } from '@headlessui/vue'

const props = defineProps(['modelValue', 'label'])
const emits = defineEmits(['input', 'change', 'update:modelValue'])

const enabled = ref(Boolean(props.modelValue))
watchEffect(() => {
	emits('input', enabled.value)
	emits('change', enabled.value)
	emits('update:modelValue', enabled.value)
})
</script>
