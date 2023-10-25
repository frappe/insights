<script setup></script>

<template>
	<div class="flex w-full justify-between">
		<div>
			<Dropdown
				:button="{
					label: 'Line',
					variant: 'outline',
					iconRight: 'chevron-down',
					iconLeft: 'table',
				}"
				:options="[{ label: 'Table' }, { label: 'Chart' }]"
			></Dropdown>
		</div>
		<div class="space-x-2">
			<Button variant="outline" label="Add to Dashboard"></Button>
			<Button variant="outline" label="Download"></Button>
			<Button variant="outline" label="Share"></Button>
		</div>
	</div>
	<div class="flex flex-1 rounded border"></div>
</template>
