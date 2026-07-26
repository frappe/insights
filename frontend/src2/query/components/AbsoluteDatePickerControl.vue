<script setup lang="ts">
import { computed } from 'vue'
import AbsoluteDatePicker from './AbsoluteDatePicker.vue'
import { formatDateFilterValue } from './formatting_utils'

const props = defineProps<{ placeholder?: string }>()

const dates = defineModel<string[]>()

const displayDate = computed(() => {
	return formatDateFilterValue('between', dates.value)
})
</script>

<template>
	<Popover class="flex w-full [&>div:first-child]:w-full">
		<template #target="{ togglePopover }">
			<input
				readonly
				type="text"
				:value="displayDate"
				:placeholder="props.placeholder || 'Select Date Range'"
				@focus="togglePopover()"
				class="form-input block h-7 w-full cursor-text select-none rounded border-gray-400 text-sm placeholder-gray-500"
			/>
		</template>
		<template #body-main="{ togglePopover }">
			<div class="flex flex-col p-2">
				<AbsoluteDatePicker v-model="dates" />
				<div class="mt-2 flex justify-end">
					<Button variant="solid" @click="togglePopover"> Done </Button>
				</div>
			</div>
		</template>
	</Popover>
</template>
