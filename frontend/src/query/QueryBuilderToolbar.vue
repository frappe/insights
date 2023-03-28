<script setup>
import { inject } from 'vue'
const builder = inject('queryBuilder')
</script>

<template>
	<div class="z-10 -mb-[1px] flex w-full overflow-hidden">
		<div
			v-for="query in builder.queries"
			:key="query.name"
			class="flex cursor-pointer items-center overflow-hidden rounded-t-md border border-b-0 border-transparent py-1.5 transition-all duration-200 ease-in-out"
			:class="
				builder.isActive(query.name)
					? 'rounded-t-md  !border-gray-200 bg-white '
					: ' hover:bg-gray-100'
			"
			@click="builder.openQuery(query.name)"
		>
			<span
				class="ml-3 max-w-[120px] overflow-hidden text-ellipsis whitespace-nowrap text-gray-600"
			>
				{{ query.doc?.title || query.name }}
			</span>
			<div
				class="cursor-pointer px-2 text-gray-500 hover:text-gray-800"
				@click.prevent.stop="builder.closeQuery(query.name)"
			>
				<FeatherIcon name="x" class="h-3.5 w-3.5"></FeatherIcon>
			</div>
		</div>

		<div class="flex items-center">
			<Button
				icon="plus"
				appearance="minimal"
				@click.prevent="builder.showNewDialog = true"
			></Button>
		</div>
	</div>
</template>
