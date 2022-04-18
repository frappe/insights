<template>
	<div class="flex h-full flex-1 items-center border-t border-gray-300 px-4 text-base text-gray-500">
		Limited to
		<input
			type="text"
			ref="limit_input"
			v-model="limit"
			:size="String(limit).length"
			class="form-input mx-1 bg-transparent py-0.5 pl-1 pr-0 font-medium text-gray-600 hover:underline focus:border-transparent focus:text-gray-600"
			@keydown.enter.stop="query.setValue.submit({ limit: limit }).then(() => $refs.limit_input.blur())"
			@keydown.esc.stop="$refs.limit_input.blur()"
		/>
		rows
	</div>
</template>

<script>
export default {
	name: 'LimitsAndOrder',
	props: ['query', 'limit'],
}
</script>
