<script setup>
import ContentEditable from '@/notebook/ContentEditable.vue'
import { Popover } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import Combobox from './Combobox.vue'

const emit = defineEmits(['update:modelValue', 'input'])
const props = defineProps({
	value: { type: Object, default: undefined },
	modelValue: Object,
	placeholder: String,
	items: { type: Array, default: () => [] },
	disableFilter: Boolean,
	disableInput: Boolean,
	placement: { type: String, default: 'bottom-start' },
})
const valuePropPassed = computed(() => props.value !== undefined)
const selectedItem = computed({
	get: () => (valuePropPassed.value ? props.value : props.modelValue),
	set: (value) => emit('update:modelValue', value),
})
const searchText = ref(selectedItem.value?.label)
watch(selectedItem, () => (searchText.value = selectedItem.value?.label))

const filteredItems = computed(() => {
	if (props.disableFilter) return props.items
	if (!searchText.value) return props.items
	if (props.items.length === 0) return []
	if (props.items.length < 10) return props.items
	return props.items.filter(
		(item) =>
			item.label?.toLowerCase().includes(searchText.value.toLowerCase()) ||
			item.value?.toLowerCase().includes(searchText.value.toLowerCase())
	)
})

function handleOptionSelect(value, togglePopover) {
	selectedItem.value = value
	searchText.value = value?.label
	togglePopover(false)
}
</script>

<template>
	<Popover :placement="placement">
		<template #target="{ togglePopover, isOpen }">
			<ContentEditable
				tag="div"
				:contenteditable="!props.disableInput"
				v-model="searchText"
				@update:model-value="
					() => {
						!isOpen && togglePopover(true)
						emit('input', searchText)
					}
				"
				@click="togglePopover"
				:placeholder="placeholder || 'Pick a value'"
				class="flex h-7 w-full cursor-pointer items-center overflow-hidden text-ellipsis !whitespace-nowrap px-2.5 leading-7 outline-none ring-0 transition-all focus:outline-none"
				:class="[
					!searchText?.length ? 'min-w-[3rem]' : '',
					!selectedItem?.label && !isOpen ? '' : '',
				]"
			/>
		</template>
		<template #body="{ togglePopover, isOpen }">
			<div
				v-show="isOpen"
				class="mt-1.5 w-fit rounded border bg-white text-base shadow-sm transition-[width]"
			>
				<slot
					name="popover"
					v-bind="{
						togglePopover,
						value: selectedItem,
						setValue: (value) => (selectedItem = value),
					}"
				>
					<Combobox
						v-model="selectedItem"
						:values="filteredItems.slice(0, 50)"
						@update:modelValue="handleOptionSelect($event, togglePopover)"
					/>
				</slot>
			</div>
		</template>
	</Popover>
</template>
