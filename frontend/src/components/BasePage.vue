<template>
	<div class="flex h-full w-full">
		<Sidebar />
		<div class="ml-[16rem] flex w-[calc(100%-16rem)] flex-1 flex-col p-6">
			<nav class="mb-4 flex" aria-label="Breadcrumb">
				<ol role="list" class="flex items-center space-x-2">
					<li>
						<div>
							<a href="#" class="text-gray-500">
								<svg
									class="h-4 w-4 flex-shrink-0"
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									aria-hidden="true"
								>
									<path
										d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"
									/>
								</svg>
								<span class="sr-only">Home</span>
							</a>
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
									'cursor-default text-gray-500 hover:no-underline':
										idx === routes.length - 1,
								}"
							>
								{{ page.name }}
							</router-link>
						</div>
					</li>
				</ol>
			</nav>
			<div
				class="flex h-[calc(100%-2.25rem)] min-h-[34rem] flex-col rounded-md border bg-white px-6 py-4 shadow-md"
			>
				<header class="mb-2 flex h-10">
					<slot name="header" />
				</header>
				<main class="flex h-[calc(100%-3rem)]">
					<slot name="main" />
				</main>
			</div>
		</div>
	</div>
</template>

<script setup>
import NavBar from '@/components/NavBar.vue'
import Sidebar from '@/components/Sidebar.vue'
import FrappeInsights from '@/components/Icons/FrappeInsights.vue'

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
