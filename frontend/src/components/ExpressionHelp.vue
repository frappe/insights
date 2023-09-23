<script setup>
defineProps({ info: Object })
</script>

<template>
	<div class="ml-auto w-[20rem] rounded border bg-white p-2 shadow-lg">
		<p>{{ info?.description }}</p>
		<div class="mt-2 rounded bg-gray-50 p-2 text-xs leading-5">
			<code>
				<span class="text-gray-600"># Syntax</span>
				<br />
				{{ info?.syntax }}
				<br />
				<br />
				<span class="text-gray-600"># Example</span>
				<br />
				{{ info?.example }}
			</code>
		</div>
	</div>
</template>
