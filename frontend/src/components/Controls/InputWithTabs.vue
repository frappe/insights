<script setup>
import Tabs from '@/components/Tabs.vue'
import { computed } from 'vue'

defineEmits(['tab-change'])
const props = defineProps(['placeholder', 'tabs', 'value'])

const tabs = computed(() =>
	Object.keys(props.tabs).map((key) => ({
		label: key,
		active: props.tabs[key],
	}))
)
function getLabel() {
	return props.value?.label || props.value
}
</script>

<template>
	<Popover class="flex w-full [&>div:first-child]:w-full" :hideOnBlur="false">
		<template #target="{ togglePopover }">
			<input
				readonly
				type="text"
				:value="getLabel()"
				:placeholder="placeholder"
				@focus="togglePopover()"
				class="form-input block h-7 w-full cursor-text select-none rounded border-gray-400 text-sm placeholder-gray-500"
			/>
		</template>
		<template #body="{ togglePopover }">
			<div
				class="my-2 flex select-none flex-col space-y-3 rounded border bg-white p-3 text-base shadow-md"
			>
				<Tabs
					:tabs="tabs"
					:model-value="getLabel()"
					@update:model-value="$emit('tab-change', $event.label)"
				/>
				<slot name="inputs"></slot>
				<div class="flex w-full justify-end">
					<Button variant="solid" @click="togglePopover()"> Done </Button>
				</div>
			</div>
		</template>
	</Popover>
</template>
