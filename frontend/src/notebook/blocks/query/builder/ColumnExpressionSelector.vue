<script setup>
import Code from '@/components/Controls/Code.vue'
import { computed } from 'vue'
import InputWithPopover from './InputWithPopover.vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({ modelValue: Object, placeholder: String })
const expression = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})
</script>

<template>
	<div class="font-code">
		<InputWithPopover
			v-model="expression"
			:disableInput="true"
			placeholder="Write an expression"
		>
			<template #popover="{ value, togglePopover, setValue }">
				<div class="h-[14rem] w-[20rem] p-2">
					<Code
						:value="value.raw"
						@inputChange="togglePopover(true)"
						@update:modelValue="
							(value) => {
								setValue({
									raw: value,
									value: value,
									label: value.replace(/\\s/g, ' '),
								})
								togglePopover(false)
							}
						"
					></Code>
				</div>
			</template>
		</InputWithPopover>
	</div>
</template>
