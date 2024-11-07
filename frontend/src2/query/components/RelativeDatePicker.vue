<script setup lang="ts">
import { computed, reactive, watchEffect } from 'vue'
import Switch from '../../components/Switch.vue'

const props = defineProps<{ placeholder: string }>()

const relativeDate = defineModel<string>({
	default: () => 'Last 1 Day',
	required: true,
})

const parts = reactive({
	span: 'Last',
	interval: '1',
	intervalType: 'Day',
})

if (relativeDate.value) {
	let [span, interval, intervalType] = relativeDate.value.split(' ')

	if (span == 'Current') {
		intervalType = interval
		interval = '1'
	}

	parts.span = span
	parts.interval = interval
	parts.intervalType = intervalType
}

watchEffect(() => {
	relativeDate.value =
		parts.span == 'Current'
			? `${parts.span} ${parts.intervalType}`
			: `${parts.span} ${parts.interval} ${parts.intervalType}`
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
		<template #body="{ togglePopover }">
			<div
				class="my-2 flex w-[16rem] select-none flex-col space-y-3 rounded border bg-white p-3 text-base shadow-md"
			>
				<Switch :tabs="['Last', 'Current', 'Next']" v-model="parts.span"></Switch>

				<div class="flex space-x-2">
					<FormControl
						v-if="parts.span !== 'Current'"
						type="number"
						v-model="parts.interval"
						class="w-full text-sm"
					/>
					<FormControl
						type="select"
						v-model="parts.intervalType"
						class="w-full text-sm"
						:options="['Day', 'Week', 'Month', 'Quarter', 'Year', 'Fiscal Year']"
					>
					</FormControl>
				</div>
				<div class="flex justify-end">
					<Button variant="solid" @click="togglePopover"> Done </Button>
				</div>
			</div>
		</template>
	</Popover>
</template>
