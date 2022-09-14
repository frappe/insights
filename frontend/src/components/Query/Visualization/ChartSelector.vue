<script setup>
defineEmits(['chartTypeChange'])
defineProps(['currentType', 'chartTypes', 'invalidTypes'])
</script>

<template>
	<div
		class="grid grid-cols-[repeat(auto-fill,3.5rem)] gap-1 overflow-scroll rounded-md bg-gray-100/90 p-1"
	>
		<div
			v-for="(chart, i) in $props.chartTypes"
			:key="i"
			class="flex flex-col items-center text-gray-500"
			:class="{
				'cursor-pointer hover:text-gray-600': !$props.invalidTypes.includes(chart.type),
				'cursor-not-allowed hover:text-gray-500': $props.invalidTypes.includes(chart.type),
			}"
			@click="$emit('chartTypeChange', chart.type)"
		>
			<div
				class="flex w-full flex-col items-center justify-center space-y-1 rounded-md py-2"
				:class="{
					' border-blue-300 bg-white text-blue-500 shadow':
						chart.type == $props.currentType,
					' border-dashed border-gray-300 opacity-60 hover:shadow-none':
						$props.invalidTypes.includes(chart.type),
				}"
			>
				<FeatherIcon :name="chart.icon" class="h-5 w-5" />
				<span
					class="text-sm"
					:class="{
						'font-normal text-blue-600': chart.type == $props.currentType,
						'font-light': chart.type != $props.currentType,
						'opacity-60': $props.invalidTypes.includes(chart.type),
					}"
				>
					{{ chart.type }}
				</span>
			</div>
		</div>
	</div>
</template>
