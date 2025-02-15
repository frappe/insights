<script setup lang="ts">
import RelativeDatePicker from './RelativeDatePicker.vue'

const props = defineProps<{ placeholder: string }>()

const relativeDate = defineModel<string>({
	default: () => 'Last 1 Day',
	required: true,
})
</script>

<template>
	<Popover class="flex w-full [&>div:first-child]:w-full">
		<template #target="{ togglePopover }">
			<input
				readonly
				type="text"
				:value="relativeDate"
				:placeholder="props.placeholder"
				@focus="togglePopover()"
				class="form-input block h-7 w-full cursor-text select-none rounded border-gray-400 text-sm placeholder-gray-500"
			/>
		</template>
		<template #body-main="{ togglePopover }">
			<div class="flex flex-col p-2">
				<RelativeDatePicker v-model="relativeDate" />
				<div class="mt-2 flex justify-end">
					<Button variant="solid" @click="togglePopover"> Done </Button>
				</div>
			</div>
		</template>
	</Popover>
</template>
