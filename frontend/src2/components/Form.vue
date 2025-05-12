<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
	fields: {
		name: string
		label: string
		type: string
		options?: string[]
		placeholder?: string
		required?: boolean
		defaultValue?: any
		description?: string
	}[]
	actions?: {
		label: string
		disabled?: boolean
		loading?: boolean
		onClick: () => void
	}[]
}>()

type Form = Record<string, any>
const form = defineModel<Form>({
	required: true,
})

props.fields.forEach((field) => {
	if (field.defaultValue) {
		form.value[field.name] = field.defaultValue
	}
})

defineExpose({
	hasRequiredFields: computed(() => {
		return props.fields.every((field) => !field.required || form.value[field.name])
	}),
})
</script>

<template>
	<div class="flex w-full flex-col gap-2">
		<div class="flex flex-col gap-4">
			<div class="relative" v-for="field in fields" :key="field.name">
				<FormControl
					autocomplete="off"
					:type="field.type"
					:label="field.label"
					:options="field.options"
					:placeholder="field.placeholder"
					:description="field.description"
					v-model="form[field.name]"
				/>
				<span
					v-if="field.required && !form[field.name]"
					class="absolute right-0 top-0 text-xs text-red-400"
				>
					* required
				</span>
			</div>
		</div>
		<div class="flex w-full justify-end gap-2 pt-2">
			<Button v-for="action in actions" :key="action.label" v-bind="action" />
		</div>
	</div>
</template>
