<template>
	<div class="flex items-center px-4 py-2 text-base text-gray-500">
		Limited to
		<span
			v-if="!editing_limit"
			class="mx-1 cursor-pointer rounded-md border border-gray-300 px-1.5 py-0.5 hover:underline"
			@click="
				() => {
					editing_limit = true
					$refs.limit_input.focus()
				}
			"
		>
			{{ limit }}
		</span>
		<input
			v-else
			type="text"
			ref="limit_input"
			v-model="limit"
			:size="String(limit).length"
			class="form-input mx-1 border border-transparent py-0.5 pl-2 pr-1.5 font-medium focus:border-transparent"
			@keydown.enter="
				() => {
					editing_limit = false
					query.setValue.submit({ limit: limit })
				}
			"
			@keydown.esc="editing_limit = false"
		/>
		rows
	</div>
</template>

<script>
export default {
	name: 'LimitsAndOrder',
	props: ['query', 'limit'],
	data() {
		return {
			editing_limit: false,
		}
	},
}
</script>
