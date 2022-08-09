<template>
	<div v-if="props.columns" class="mt-2 flex h-full w-full flex-col text-base">
		<div class="sticky top-0 flex w-full rounded-md bg-gray-100">
			<div
				v-for="column in props.columns"
				class="flex-1 px-2.5 py-1.5 font-medium text-gray-600"
				scope="col"
			>
				{{ column }}
			</div>
		</div>
		<div class="flex flex-col">
			<div v-for="row in props.rows" class="flex">
				<div
					v-for="cell in row"
					class="flex-1 bg-white p-2.5 pr-4 font-light text-gray-600"
				>
					{{ cell }}
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	columns: {
		type: Array,
	},
	rows: {
		type: Array,
	},
})
</script>
