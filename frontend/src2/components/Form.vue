<script setup lang="ts">
import { computed, watch } from 'vue'

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
		dependsOn?: string
	}[]
	actions?: {
		label: string
		disabled?: boolean
		loading?: boolean
		onClick: () => void
	}[]
}>()

type Field = (typeof props.fields)[number]
type Form = Record<string, any>
const form = defineModel<Form>({
	required: true,
})

props.fields.forEach((field) => {
	if (field.defaultValue) {
		form.value[field.name] = field.defaultValue
	}
})

function isVisible(field: Field) {
	return !field.dependsOn || Boolean(form.value[field.dependsOn])
}

// A hidden field is not part of the form. Vue keeps whatever its input last
// held, so without this it would still submit after its dependency turns off.
watch(
	() => props.fields.map(isVisible),
	(visible) => {
		props.fields.forEach((field, index) => {
			if (!visible[index]) delete form.value[field.name]
		})
	},
	{ immediate: true },
)

defineExpose({
	hasRequiredFields: computed(() => {
		return props.fields.every(
			(field) => !field.required || !isVisible(field) || form.value[field.name],
		)
	}),
})
</script>

<template>
	<div class="flex w-full flex-col gap-2">
		<div class="flex flex-col gap-4">
			<template v-for="field in fields" :key="field.name">
				<div class="relative" v-if="isVisible(field)">
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
						class="absolute right-0 top-0 text-xs text-ink-red-5"
					>
						* required
					</span>
				</div>
			</template>
		</div>
		<div class="flex w-full justify-end gap-2 pt-2">
			<Button v-for="action in actions" :key="action.label" v-bind="action" />
		</div>
	</div>
</template>
