<template>
	<div>
		<div class="flex items-center space-x-2">
			<div class="rounded bg-gray-100 p-1">
				<FeatherIcon name="arrow-up-right" class="h-4 w-4" />
			</div>
			<div class="text-lg">Quick Actions</div>
		</div>
		<div class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
			<div
				class="col-span-1 flex cursor-pointer items-center justify-between rounded border border-transparent bg-white p-4 shadow transition-all hover:border-gray-400"
				@click="$router.push('/data-source#new')"
			>
				<div class="text-lg font-medium text-gray-900">Connect Data Source</div>
				<div class="rounded bg-gray-100 p-1">
					<FeatherIcon name="plus" class="h-4 w-4 text-gray-900" />
				</div>
			</div>
			<div
				class="col-span-1 flex cursor-pointer items-center justify-between rounded border border-transparent bg-white p-4 shadow transition-all hover:border-gray-400"
				@click="$router.push('/query#new')"
			>
				<div class="text-lg font-medium text-gray-900">Create a Query</div>
				<div class="rounded bg-gray-100 p-1">
					<FeatherIcon name="plus" class="h-4 w-4 text-gray-900" />
				</div>
			</div>
			<div
				class="col-span-1 flex cursor-pointer items-center justify-between rounded border border-transparent bg-white p-4 shadow transition-all hover:border-gray-400"
				@click="$router.push('/dashboard#new')"
			>
				<div class="text-lg font-medium text-gray-900">Create a Dashboard</div>
				<div class="rounded bg-gray-100 p-1">
					<FeatherIcon name="plus" class="h-4 w-4 text-gray-900" />
				</div>
			</div>
		</div>
	</div>
</template>
