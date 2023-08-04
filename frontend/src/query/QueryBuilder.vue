<script setup>
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import Query from '@/query/Query.vue'

const props = defineProps({ name: String })
</script>

<template>
	<header class="sticky top-0 z-10 flex items-center justify-between bg-white px-5 py-2.5">
		<PageBreadcrumbs
			class="h-7"
			:items="[
				{ label: 'Queries', route: { path: '/query' } },
				{
					label: props.name,
					route: { path: `/query/build/${props.name}` },
				},
			]"
		/>
	</header>
	<div class="flex h-full w-full flex-col overflow-hidden bg-white px-4 py-1">
		<Query :name="props.name" />
	</div>
</template>
