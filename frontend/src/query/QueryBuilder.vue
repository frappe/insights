<script setup>
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import Query from '@/query/Query.vue'
const props = defineProps({ name: String })
</script>

<template>
	<div class="flex h-full w-full flex-col overflow-hidden bg-white px-6 py-4">
		<Breadcrumbs
			:items="[
				{
					label: 'Query',
					href: '/query',
				},
				{
					label: props.name,
					href: `/query/build/${props.name}`,
				},
			]"
		>
		</Breadcrumbs>
		<div class="-mx-1 flex w-full flex-1 flex-col overflow-hidden py-3">
			<Query :name="props.name" />
		</div>
	</div>
</template>
