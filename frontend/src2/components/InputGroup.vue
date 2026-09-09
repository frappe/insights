<script setup lang="ts">
import { TextInput } from 'frappe-ui'
import { computed } from 'vue'
import { startDrag } from '../helpers/drag'

/**
 * One control made of several fields, after Builder's box controls.
 *
 * Prefix, suffix and precision are three readings of one question — how a
 * number prints — the way the four sides of a margin are one question. So they
 * share a frame and read as one control, and each field carries its own name
 * under it rather than beside it, which is what let them be side by side at all.
 *
 * Two things a plain row of controls does not do:
 *
 *   - The placeholder states what the field inherits. A panel field mostly
 *     states nothing, and an author needs to read the answer either way.
 *   - The name under a number field is its handle. Drag it, or press an arrow
 *     key in the field, and the number steps. A precision is nudged far more
 *     often than it is typed.
 */
export type InputGroupField = {
	key: string
	/** The name under the field. For a number, also the drag handle. */
	label: string
	value?: string | number
	/** What the field prints when it states nothing. */
	placeholder?: string
	type?: 'text' | 'number'
	min?: number
	max?: number
	step?: number
}

const props = defineProps<{ fields: InputGroupField[] }>()

// eslint-disable-next-line no-unused-vars
const emit = defineEmits<{ update: [key: string, value: string] }>()

const columns = computed(() => ({
	gridTemplateColumns: `repeat(${props.fields.length}, minmax(0, 1fr))`,
}))

function steps(field: InputGroupField) {
	return field.type === 'number'
}

function step(field: InputGroupField, by: number) {
	const from = Number(field.value)
	const low = field.min ?? -Infinity
	const high = field.max ?? Infinity
	const next = (isNaN(from) ? 0 : from) + by * (field.step ?? 1)
	emit('update', field.key, String(Math.min(high, Math.max(low, next))))
}

function onKeydown(event: KeyboardEvent, field: InputGroupField) {
	if (!steps(field)) return
	if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return
	event.preventDefault()
	step(field, event.key === 'ArrowUp' ? 1 : -1)
}

function onLabelDrag(event: MouseEvent, field: InputGroupField) {
	if (!steps(field)) return
	event.preventDefault()

	const from = Number(field.value)
	const start = isNaN(from) ? 0 : from
	const startY = event.clientY

	startDrag({
		cursor: 'ns-resize',
		onMove: (moved) => {
			const by = Math.round(startY - moved.clientY)
			const low = field.min ?? -Infinity
			const high = field.max ?? Infinity
			const next = start + by * (field.step ?? 1)
			emit('update', field.key, String(Math.min(high, Math.max(low, next))))
		},
	})
}
</script>

<template>
	<div class="w-full">
		<!--
		The frame owns the fill and the rounding, and a hairline is the only thing
		between one field and the next. The fields are `ghost`, so no field draws a
		box of its own inside a box. A focused field takes the base surface and
		lifts out of the group, which is the only state that needs an edge.
		-->
		<div
			class="flex divide-x divide-outline-gray-2 overflow-hidden rounded-4 bg-surface-gray-2"
		>
			<TextInput
				v-for="field in props.fields"
				:key="field.key"
				variant="ghost"
				class="min-w-0 flex-1 [&_input]:h-7 [&_input]:rounded-none [&_input]:bg-transparent [&_input]:px-1 [&_input]:text-center [&_input]:text-xs [&_input]:hover:bg-surface-gray-3 [&_input]:focus:bg-surface-base"
				:type="field.type || 'text'"
				:aria-label="field.label"
				:placeholder="field.placeholder"
				:modelValue="field.value as any"
				:min="field.min"
				:max="field.max"
				:step="field.step"
				@update:modelValue="emit('update', field.key, String($event))"
				@keydown="onKeydown($event, field)"
			/>
		</div>

		<div class="mt-1 grid" :style="columns">
			<span
				v-for="field in props.fields"
				:key="`label-${field.key}`"
				class="select-none truncate text-center text-[10px] leading-4 text-ink-gray-4"
				:class="steps(field) ? 'cursor-ns-resize' : ''"
				:title="field.label"
				@mousedown="onLabelDrag($event, field)"
			>
				{{ field.label }}
			</span>
		</div>
	</div>
</template>

<style scoped>
/* The label is the handle, and a spinner crowds a field this narrow. */
:deep(input[type='number']::-webkit-outer-spin-button),
:deep(input[type='number']::-webkit-inner-spin-button) {
	appearance: none;
	margin: 0;
}

:deep(input[type='number']) {
	appearance: textfield;
}
</style>
