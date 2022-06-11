<template>
	<Popover class="flex w-full [&>div:first-child]:w-full">
		<template #target="{ togglePopover }">
			<input
				readonly
				type="text"
				:value="modelValue?.label"
				:placeholder="placeholder"
				@focus="togglePopover()"
				class="form-input block h-8 w-full cursor-text select-none rounded-md text-sm placeholder-gray-500"
			/>
		</template>
		<template #body="{ togglePopover }">
			<div
				class="my-2 flex w-[18rem] select-none flex-col space-y-3 rounded-md border border-gray-50 bg-white p-3 text-base shadow"
			>
				<div class="flex h-8 items-center space-x-2 rounded-md border bg-gray-50 p-0.5 text-sm">
					<div
						class="flex h-full flex-1 items-center justify-center rounded-md border border-transparent font-light"
						:class="{ 'border border-gray-200 bg-white font-normal shadow-sm': span == 'Last' }"
						@click.prevent.stop="span = 'Last'"
					>
						Last
					</div>
					<div
						class="flex h-full flex-1 items-center justify-center rounded-md border border-transparent"
						:class="{ 'border border-gray-200 bg-white font-normal shadow-sm': span == 'Current' }"
						@click.prevent.stop="span = 'Current'"
					>
						Current
					</div>
				</div>
				<div class="flex space-x-2">
					<Input v-if="span !== 'Current'" type="number" v-model="interval" class="h-8 w-full text-sm" />
					<Input
						type="select"
						v-model="interval_type"
						class="h-8 w-full text-sm"
						:options="
							span === 'Current'
								? ['Day', 'Week', 'Month', 'Quarter', 'Year']
								: ['Days', 'Weeks', 'Months', 'Quarters', 'Years']
						"
					>
					</Input>
				</div>
				<div class="flex justify-end">
					<Button
						appearance="primary"
						@click="
							() => {
								apply()
								togglePopover()
							}
						"
					>
						Done
					</Button>
				</div>
			</div>
		</template>
	</Popover>
</template>

<script>
export default {
	name: 'TimespanPicker',
	props: ['modelValue', 'placeholder'],
	data() {
		const [span, interval, interval_type] = this.modelValue?.value?.split(' ') || ['Last', '1', 'Days']
		return {
			span,
			interval,
			interval_type,
		}
	},
	computed: {
		value() {
			return this.span === 'Current'
				? `${this.span} ${this.interval_type}`
				: `${this.span} ${this.interval} ${this.interval_type}`
		},
		label() {
			return this.value
		},
	},
	watch: {
		span(new_val) {
			this.interval_type = new_val === 'Current' ? 'Day' : 'Days'
		},
		interval(new_val) {
			if (new_val < 1) {
				this.interval = 1
			}
		},
	},
	methods: {
		apply() {
			this.$emit('update:modelValue', {
				label: this.value,
				value: this.value,
			})
			this.$emit('change', {
				label: this.value,
				value: this.value,
			})
		},
	},
}
</script>
