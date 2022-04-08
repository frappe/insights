<template>
	<div class="sticky top-0 z-10 flex h-16 flex-shrink-0 bg-white shadow">
		<div class="mx-auto flex max-w-7xl flex-1 justify-end px-8">
			<div class="relative flex py-3">
				<Input
					type="text"
					name="table-search"
					autocomplete="off"
					class="block h-full w-96 rounded-md border-gray-300 text-sm focus:border-gray-300 focus:bg-white focus:shadow focus:outline-0 focus:ring-0"
					placeholder="Search"
				/>
				<div class="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
					<FeatherIcon name="search" class="h-4 w-4 text-gray-400" aria-hidden="true" />
				</div>
			</div>
			<div class="ml-6 flex h-full cursor-pointer items-center">
				<FeatherIcon name="bell" class="h-5 w-5 text-gray-600" aria-hidden="true" />
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
</template>
