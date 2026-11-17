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
		<template #trigger>
			<input
				readonly
				type="text"
				:value="relativeDate"
				:placeholder="props.placeholder"
				class="form-input block h-7 w-full cursor-text select-none rounded-4 border-outline-gray-3 text-sm placeholder-ink-gray-4"
			/>
		</template>
		<template #default="{ close }">
			<!-- The popover sets no width, so the picker's width is set here. -->
			<div class="flex w-60 flex-col p-2">
				<RelativeDatePicker v-model="relativeDate" />
				<div class="mt-2 flex justify-end">
					<Button variant="solid" @click="close"> Done </Button>
				</div>
			</div>
		</template>
	</Popover>
</template>
