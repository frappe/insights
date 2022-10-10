<template>
	<div>
		<div class="mb-1 text-sm text-gray-600" v-if="label">
			{{ label }}
		</div>
		<Popover placement="bottom-start" class="w-full">
			<template #target="{ togglePopover }">
				<div
					tabindex="0"
					:class="inputClass"
					class="flex h-8 w-full items-center rounded-md bg-gray-100 px-3 placeholder-gray-500 focus:outline-none"
					@click="togglePopover()"
				>
					<div class="flex items-center">
						<div
							v-if="value"
							class="mr-1 h-3 w-3 rounded"
							:style="{ backgroundColor: value }"
						></div>
						<span v-if="value">
							{{ selectedColorLabel }}
						</span>
						<span class="text-gray-400" v-else>
							{{ placeholder || label }}
						</span>
					</div>
				</div>
			</template>
			<template #body>
				<div class="mt-1 w-fit rounded-md border bg-white p-3 pt-2 text-center shadow-md">
					<div>
						<div class="inline-grid grid-cols-5 gap-3 border-b border-none">
							<div class="col-span-5 text-left text-base">Pick a color</div>
							<div
								v-for="color in colors"
								:key="color"
								class="h-5 w-5 cursor-pointer rounded"
								:style="{ backgroundColor: color }"
								@click="setColorValue(color)"
							></div>
							<input
								ref="input"
								type="text"
								:value="value"
								placeholder="Custom Hex"
								:class="inputClass"
								class="col-span-5 flex h-8 items-center rounded-md border-0 bg-gray-100 px-3 text-base placeholder-gray-500 focus:outline-none"
								@change="(e) => setColorValue(e.target.value)"
							/>
						</div>
					</div>
				</div>
			</template>
		</Popover>
	</div>
</template>

<script>
export default {
	name: 'Color',
	props: {
		label: String,
		modelValue: String,
		inputClass: String,
		placeholder: String,
		autofocus: Boolean,
	},
	emits: ['focus', 'update:modelValue'],
	mounted() {
		if (this.autofocus) {
			this.focus()
		}
	},
	methods: {
		focus() {
			if (this.$refs.input && this.$refs.input.focus) {
				this.$refs.input.focus()
			}
		},
		setColorValue(value) {
			if (!value.startsWith('#')) {
				value = '#' + value
			}
			if (/^#[0-9A-F]{6}$/i.test(value)) {
				this.triggerChange(value)
			}
		},
		triggerChange(value) {
			if (value === '') {
				value = null
			}
			this.$emit('update:modelValue', value)
		},
	},
	computed: {
		value: {
			get() {
				return this.modelValue
			},
			set(value) {
				this.setColorValue(value)
			},
		},
		colors() {
			return ['#23546B', '#2F7A8B', '#3B9FAA', '#47C5C9', '#53ECE9']
		},
		selectedColorLabel() {
			const color = this.colors.find((c) => this.value === c.value)
			return color ? color.label : this.value
		},
	},
}
</script>
