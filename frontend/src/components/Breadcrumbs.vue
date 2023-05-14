<template>
	<nav>
		<ol
			role="list"
			class="flex h-5 flex-shrink-0 items-center space-x-1 font-light text-gray-800"
		>
			<li class="flex items-center">
				<router-link to="/" class="mr-1">
					<HomeIcon class="h-4 w-4" />
				</router-link>
				<FeatherIcon
					name="chevron-right"
					class="h-4 w-4 flex-shrink-0"
					aria-hidden="true"
				/>
			</li>
			<li v-for="(page, idx) in items" :key="page.label">
				<div class="flex items-center">
					<router-link
						:to="idx === items.length - 1 ? '#' : page.href"
						class="mr-1 hover:underline"
						:class="{
							'cursor-default  hover:no-underline': idx === items.length - 1,
						}"
					>
						{{ page.label }}
					</router-link>
					<FeatherIcon
						v-if="idx !== items.length - 1"
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
import HomeIcon from '@/components/Icons/HomeIcon.vue'

const props = defineProps({ items: Array })
</script>
