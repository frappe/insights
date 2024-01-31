<template>
	<Popover trigger="hover" :hoverDelay="hoverDelay" :placement="placement">
		<template #target>
			<slot />
		</template>
		<template #body>
			<slot name="body">
				<div
					class="w-fit rounded bg-gray-800 px-2 py-1 text-center text-xs text-white shadow-xl"
					:class="bodyClasses"
				>
					{{ text }}
				</div>
			</slot>
		</template>
	</Popover>
</template>
<script>
export default {
	name: 'Tooltip',
	props: {
		hoverDelay: {
			default: 0.5,
		},
		placement: {
			default: 'bottom',
		},
		text: {
			type: String,
			default: '',
		},
		bodyClasses: {
			type: String,
			default: '',
		},
	},
}
</script>
