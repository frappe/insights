<template>
	<nav>
		<ol role="list" class="flex h-7 items-start space-x-1 text-sm font-light text-gray-500">
			<li v-for="(page, idx) in props.routes" :key="page.name">
				<div class="flex items-center">
					<router-link
						:to="idx === routes.length - 1 ? '#' : `/${page.path}`"
						class="mr-1 text-gray-600 hover:underline"
						:class="{
							'cursor-default hover:no-underline': idx === routes.length - 1,
						}"
					>
						{{ page.name }}
					</router-link>
					<FeatherIcon
						v-if="idx !== routes.length - 1"
						name="chevron-right"
						class="h-4 w-4 flex-shrink-0"
						aria-hidden="true"
					/>
				</div>
			</li>
		</ol>
	</nav>
</template>

<script setup>
const props = defineProps({
	routes: {
		type: Array,
		required: true,
	},
})
</script>
