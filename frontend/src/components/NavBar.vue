<template>
	<!-- mx-auto flex h-14 w-full max-w-[85rem] flex-col items-center justify-center bg-white px-4 shadow-sm sm:px-6 lg:px-8 -->
	<div
		class="sticky top-0 z-10 mx-auto flex w-full max-w-[85rem] flex-shrink-0 px-4 sm:px-6 lg:px-8"
	>
		<!-- Breadcrumbs -->
		<nav class="flex" aria-label="Breadcrumb">
			<ol role="list" class="flex items-center space-x-2">
				<li>
					<div>
						<router-link to="/">
							<FrappeInsights />
						</router-link>
					</div>
				</li>
				<li v-for="(page, idx) in routes" :key="page.name">
					<div class="flex items-center text-sm">
						<FeatherIcon
							name="chevron-right"
							class="h-5 w-5 flex-shrink-0 text-gray-500"
							aria-hidden="true"
						/>
						<router-link
							:to="idx === routes.length - 1 ? '#' : page.path"
							class="ml-2 text-gray-600 hover:underline"
							:class="{
								'cursor-default text-gray-500 hover:no-underline': idx === routes.length - 1,
							}"
						>
							{{ page.name }}
						</router-link>
					</div>
				</li>
			</ol>
		</nav>
		<!-- Searchbar -->
		<div class="flex flex-1 justify-end">
			<div class="relative flex py-3">
				<Input
					type="text"
					name="search-bar"
					autocomplete="off"
					class="block h-full w-96 rounded-md border-gray-300 text-sm focus:border-gray-300 focus:bg-white focus:shadow focus:outline-0 focus:ring-0"
					placeholder="Search for anything..."
				/>
				<div class="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
					<FeatherIcon name="search" class="h-4 w-4 text-gray-400" aria-hidden="true" />
				</div>
			</div>
			<div class="ml-4 flex h-full cursor-pointer items-center">
				<Avatar
					v-if="$user().full_name"
					:label="$user().full_name"
					:imageURL="$user().user_image"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import FrappeInsights from '@/components/Icons/FrappeInsights.vue'

import { Avatar } from 'frappe-ui'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const routes = computed(() =>
	route.path
		.split('/')
		.filter(Boolean)
		.map((route) => {
			return {
				name: route.charAt(0).toUpperCase() + route.slice(1),
				path: `/${route}`,
			}
		})
)
</script>
