<template>
	<div class="sticky top-0 z-10 flex h-14 flex-shrink-0 bg-white px-8">
		<div class="mx-auto flex max-w-7xl flex-1 px-8">
			<!-- Breadcrumbs -->
			<nav class="flex" aria-label="Breadcrumb">
				<ol role="list" class="flex items-center space-x-2">
					<li>
						<div>
							<a href="#">
								<img class="app-logo" style="width: 20px" src="/assets/frappe/images/frappe-framework-logo.svg" />
							</a>
						</div>
					</li>
					<li v-for="(page, idx) in routes" :key="page.name">
						<div class="flex items-center text-sm">
							<FeatherIcon name="chevron-right" class="h-5 w-5 flex-shrink-0 text-gray-500" aria-hidden="true" />
							<a
								:href="idx === routes.length - 1 ? '#' : page.path"
								class="ml-2 text-gray-600 hover:underline"
								:class="{ 'cursor-default text-gray-500 hover:no-underline': idx === routes.length - 1 }"
							>
								{{ page.name }}
							</a>
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
				<div class="ml-6 flex h-full cursor-pointer items-center">
					<img
						class="h-8 w-8 rounded-full"
						src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80"
						alt=""
					/>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	computed: {
		routes() {
			return this.$route.path
				.split('/')
				.filter(Boolean)
				.map((route) => {
					return {
						name: route.charAt(0).toUpperCase() + route.slice(1),
						path: `/${route}`,
					}
				})
		},
	},
}
</script>
