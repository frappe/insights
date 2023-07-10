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
				class="form-input block h-8 w-full cursor-text select-none rounded-lg text-sm placeholder-gray-500"
			/>
		</template>
		<template #body="{ togglePopover }">
			<div
				class="my-2 flex select-none flex-col space-y-3 rounded-lg border bg-white p-3 text-base shadow-md"
			>
				<Tabs :tabs="tabs" @switch="$emit('tab-change', $event.label)" />
				<slot name="inputs"></slot>
				<div class="flex w-full justify-end">
					<Button
						appearance="primary"
						@click="togglePopover()"
						class="!rounded-lg bg-gray-900 text-gray-50 hover:bg-gray-800"
					>
						Done
					</Button>
				</div>
			</div>
		</template>
	</Popover>
</template>
