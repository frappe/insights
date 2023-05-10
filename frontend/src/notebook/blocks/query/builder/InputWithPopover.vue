<script setup>
import { Popover } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import ContentEditable from '@/notebook/ContentEditable.vue'
import Combobox from './Combobox.vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	value: { type: Object, default: undefined },
	modelValue: Object,
	placeholder: String,
	items: Array,
	disableFilter: Boolean,
	disableInput: Boolean,
})
const valuePropPassed = props.value !== undefined
const selectedItem = computed({
	get: () => (valuePropPassed ? props.value : props.modelValue),
	set: (value) => emit('update:modelValue', value),
})
const searchText = ref(selectedItem.value?.label)
watch(selectedItem, () => (searchText.value = selectedItem.value?.label))

const filteredItems = computed(() => {
	if (props.disableFilter) return props.items
	if (!searchText.value) return props.items
	return props.items.filter(
		(item) =>
			item.label.toLowerCase().includes(searchText.value.toLowerCase()) ||
			item.value.toLowerCase().includes(searchText.value.toLowerCase())
	)
})
</script>

<template>
	<Popover placement="bottom-start">
		<template #target="{ togglePopover, isOpen }">
			<ContentEditable
				tag="div"
				:contenteditable="!props.disableInput"
				v-model="searchText"
				@update:model-value="!isOpen && togglePopover(true)"
				@click="togglePopover"
				:placeholder="placeholder || 'Pick a value'"
				class="cursor-pointer px-2.5 py-0.5 outline-none ring-0 transition-all focus:outline-none"
				:class="[
					!searchText?.length ? 'min-w-[3rem]' : '',
					!selectedItem.label && !isOpen ? '' : '',
				]"
			/>
		</template>
		<template #body="{ togglePopover, isOpen }">
			<div
				v-show="isOpen"
				class="mt-1.5 w-fit rounded-lg border bg-white text-base shadow transition-[width]"
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
						:values="filteredItems"
						@update:modelValue="togglePopover()"
					/>
				</slot>
			</div>
		</template>
	</Popover>
</template>
