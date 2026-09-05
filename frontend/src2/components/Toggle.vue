<template>
	<!--
	`Switch` spaces itself as a settings row: a label-only row carries `py-1.5`
	so a list of them abuts. Insights uses it as one control in a gapped form
	stack, where that padding lands on top of the gap and doubles it. Cancelling
	it here makes a Toggle measure like every other control in the stack, so the
	stack's own gap is the only thing setting the rhythm.
	-->
	<Switch
		v-bind="$attrs"
		v-model="checked"
		:size="props.size || 'sm'"
		:disabled="props.disabled"
		class="-my-1.5"
	>
		<template v-if="props.label" #label>
			<span class="text-xs text-ink-gray-5">{{ props.label }}</span>
		</template>
	</Switch>
</template>

<script setup lang="ts">
import { Switch } from 'frappe-ui'
import { computed } from 'vue'

// Callers bind Frappe check fields straight to this, which hold 0 and 1.
const model = defineModel<Boolean | Number>()
const checked = computed({
	get: () => Boolean(model.value),
	set: (value: boolean) => (model.value = value),
})

const props = defineProps<{
	label?: string
	size?: 'sm' | 'md'
	disabled?: boolean
}>()
</script>
