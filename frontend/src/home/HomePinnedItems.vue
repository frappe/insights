<template>
	<div>
		<div class="flex items-center space-x-2">
			<div class="rounded bg-gray-100 p-1">
				<FeatherIcon name="bookmark" class="h-4 w-4" />
			</div>
			<div class="text-lg">Pinned Items</div>
		</div>
		<div class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
			<div
				class="col-span-1 flex cursor-pointer items-center space-x-2 rounded border border-dashed bg-gray-50 p-4 transition-all hover:border-gray-400"
			>
				<div class="rounded p-1">
					<FeatherIcon name="plus" class="h-4 w-4 text-gray-600" />
				</div>
				<div class="text-lg font-medium text-gray-600">Pin an item</div>
			</div>
		</div>
	</div>
</template>
