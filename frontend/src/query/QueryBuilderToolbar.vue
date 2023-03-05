<script setup>
import { inject } from 'vue'
const builder = inject('queryBuilder')
</script>

<template>
	<div class="z-10 -mb-[1px] flex">
		<div
			v-for="query in builder.queries"
			:key="query.name"
			class="flex cursor-pointer items-center rounded-t-md border border-b-0 border-transparent px-2 transition-all duration-200 ease-in-out"
			:class="
				builder.isActive(query.name)
					? 'rounded-t-md  !border-gray-200 bg-white '
					: ' hover:bg-gray-100'
			"
			@click="builder.openQuery(query.name)"
		>
			<div class="flex items-center gap-1 py-1.5 px-2">
				<FeatherIcon
					v-if="query.doc?.is_stored"
					name="bookmark"
					class="h-3 w-3"
					:class="builder.isActive(query.name) ? 'text-blue-500' : 'text-gray-400'"
					fill="currentColor"
				></FeatherIcon>

				<span
					class="max-w-[200px] overflow-hidden text-ellipsis whitespace-nowrap text-gray-600"
				>
					{{ query.name }}
				</span>
			</div>

			<div
				class="cursor-pointer p-1.5 text-gray-500 hover:text-gray-800"
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
