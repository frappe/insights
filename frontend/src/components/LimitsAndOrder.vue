<template>
	<div class="flex h-full flex-1 items-center justify-between text-base text-gray-500">
		<div v-if="order_bys.length">
			<span> Sorted by </span>
			<span v-for="(order_by, idx) in order_bys" :key="idx">
				<span class="font-medium text-gray-600">{{ order_by.column }}</span> {{ order_by.order }}
				<span v-if="idx < order_bys.length - 1">, </span>
			</span>
		</div>
		<div class="ml-auto">
			<span>Limited to</span>
			<input
				type="text"
				ref="limit_input"
				v-model.number="limit"
				:size="String(limit).length"
				class="form-input mx-1 bg-gray-100 py-0.5 pl-2 pr-1 font-medium text-gray-600 hover:underline focus:border-transparent focus:bg-gray-200 focus:text-gray-600"
				@keydown.enter.stop="set_limit"
				@keydown.esc.stop="$refs.limit_input.blur()"
			/>
			<span>rows</span>
		</div>
	</div>
</template>

<script>
export default {
	name: 'LimitsAndOrder',
	props: ['query'],
	data() {
		return {
			limit: this.query.doc.limit,
		}
	},
	computed: {
		order_bys() {
			return this.query.doc.columns
				.filter((c) => c.order_by)
				.map((c) => ({
					column: c.label,
					order: c.order_by,
				}))
		},
	},
	methods: {
		set_limit() {
			const sanitized_limit = parseInt(this.limit, 10)
			if (sanitized_limit > 0) {
				this.query.set_limit.submit({ limit: sanitized_limit }).then(() => this.$refs.limit_input.blur())
			} else {
				this.limit = this.query.doc.limit
				this.$notify({
					color: 'red',
					icon: 'alert-circle',
					title: 'Invalid Limit',
					message: 'Limit must be a positive integer',
				})
				this.$refs.limit_input.blur()
			}
		},
	},
}
</script>
