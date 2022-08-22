<template>
	<div class="h-full w-full">
		<div class="h-5 text-base font-semibold text-gray-600">{{ props.title }}</div>
		<div
			class="relative mt-2 flex h-[calc(100%-1.5rem)] w-full flex-col overflow-scroll text-base scrollbar-hide"
		>
			<table v-if="props.columns">
				<thead class="sticky top-0">
					<tr>
						<td
							v-for="column in props.columns"
							class="whitespace-nowrap bg-gray-100 px-2.5 py-1.5 font-medium text-gray-600 first:rounded-l-md last:rounded-r-md"
							scope="col"
						>
							{{ column }}
						</td>
					</tr>
				</thead>
				<tbody>
					<tr v-for="row in props.rows">
						<td
							v-for="cell in row"
							class="whitespace-nowrap bg-white p-2.5 font-light text-gray-600"
						>
							{{ cell }}
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	title: {
		type: String,
		default: '',
	},
	columns: {
		type: Array,
	},
	rows: {
		type: Array,
	},
})
</script>
