<template>
	<Popover class="flex w-full [&>div:first-child]:w-full">
		<template #target="{ togglePopover }">
			<input
				readonly
				type="text"
				:value="_value"
				:placeholder="placeholder"
				@focus="togglePopover()"
				class="form-input block h-7 w-full cursor-text select-none rounded border-gray-400 text-sm placeholder-gray-500"
			/>
		</template>
		<template #body="{ togglePopover }">
			<div
				class="my-2 flex w-[18rem] select-none flex-col space-y-3 rounded border bg-white p-3 text-base shadow-md"
			>
				<Tabs :tabs="['Last', 'Current', 'Next']" v-model="span"></Tabs>

				<div class="flex space-x-2">
					<Input
						v-if="span !== 'Current'"
						type="number"
						v-model="interval"
						class="w-full text-sm"
					/>
					<Input
						type="select"
						v-model="intervalType"
						class="w-full text-sm"
						:options="['Day', 'Week', 'Month', 'Quarter', 'Year', 'Fiscal Year']"
					>
					</Input>
				</div>
				<div class="flex justify-end">
					<Button
						variant="solid"
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
import Tabs from '@/components/Tabs.vue'

export default {
	name: 'TimespanPicker',
	components: { Tabs },
	emits: ['update:modelValue', 'change'],
	props: ['value', 'modelValue', 'placeholder'],
	data() {
		const initalValue = (this.valuePropPassed() ? this.value : this.modelValue?.value) || ''
		let [span, interval, intervalType] = initalValue.split(' ')

		if (span == 'Current') intervalType = interval // eg. Current Day
		if (intervalType?.at(-1) == 's') intervalType = intervalType.slice(0, -1) // eg. Days

		return {
			span: span || 'Last',
			interval: interval || '1',
			intervalType: intervalType || 'Day',
		}
	},
	computed: {
		_value() {
			return this.span === 'Current'
				? `${this.span} ${this.intervalType}`
				: `${this.span} ${this.interval} ${this.intervalType}`
		},
	},
	watch: {
		interval(new_val) {
			if (new_val < 1) {
				this.interval = 1
			}
		},
	},
	methods: {
		valuePropPassed() {
			return this.value !== undefined
		},
		apply() {
			if (this.valuePropPassed()) {
				this.$emit('change', this._value)
			} else {
				this.$emit('update:modelValue', {
					value: this._value,
					label: this._value,
				})
			}
		},
	},
}
</script>
