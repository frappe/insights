<script setup>
import { computed, inject } from 'vue'

const $utils = inject('$utils')
const props = defineProps({
	data: { type: Object, required: true },
	options: { type: Object, required: true },
})

const formattedValue = computed(() => {
	if (!props.data?.length) return
	if (!props.options.column) return
	const _value = props.data.reduce((acc, row) => {
		return acc + row[props.options.column]
	}, 0)

	if (!props.options.hasOwnProperty('shorten') || props.options.shorten) {
		return $utils.getShortNumber(_value, props.options.decimals)
	}
	return $utils.formatNumber(_value, props.options.decimals)
})
</script>

<template>
	<div
		v-if="formattedValue"
		class="flex h-full w-full items-center justify-center overflow-hidden px-8 py-4"
	>
		<div
			class="mx-auto flex h-full max-h-[10rem] w-full min-w-40 max-w-[20rem] flex-col justify-center overflow-y-auto"
		>
			<div class="w-full">
				<span class="truncate font-medium leading-6">{{ props.options.title }}</span>
			</div>
			<div class="text-[28px] font-medium leading-10">
				{{ props.options.prefix }}{{ formattedValue }}{{ props.options.suffix }}
			</div>
		</div>
	</div>
	<template v-else>
		<slot name="placeholder"></slot>
	</template>
</template>
