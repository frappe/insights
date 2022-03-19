<!-- This example requires Tailwind CSS v2.0+ -->
<template>
	<div class="filter-search relative z-10 w-full rounded-md shadow-sm">
		<input
			type="text"
			ref="filter_search"
			spellcheck="false"
			class="block w-full select-none rounded-md border-gray-300 text-sm text-transparent caret-black focus:border-gray-300 focus:shadow focus:outline-0 focus:ring-0"
			:class="{ 'font-semibold': filter_right }"
			:placeholder="focused ? placeholder : 'Add a filter...'"
			v-model="input_value"
			@focus="focused = true"
			@keydown.backspace="on_backspace"
			@keydown.meta.enter="on_enter"
			@keydown.ctrl.enter="on_enter"
		/>
		<div
			v-if="input_value"
			class="absolute top-0 block w-full cursor-text border border-transparent py-2 px-3 text-sm leading-6"
		>
			<span class="mr-1 font-medium">{{ filter_left }}</span>

			<span
				v-if="left_selected && !filter_operator"
				class="mr-1 text-xs font-light text-slate-400"
			>
				{{ placeholder }}
			</span>
			<span v-else class="mr-1 font-light"> {{ filter_operator }} </span>

			<span
				v-if="left_selected && operator_selected && !filter_right"
				class="mr-1 text-xs font-light text-slate-400"
			>
				{{ placeholder }}
			</span>
			<span v-else class="font-semibold text-green-600">
				{{ filter_right }}
			</span>
		</div>
		<div
			class="absolute inset-y-0 right-0 flex items-center pr-3 transition-all hover:scale-110"
		>
			<FeatherIcon
				name="check-circle"
				class="h-4 w-4 cursor-pointer text-gray-400"
				:class="{
					'text-green-500': filter_left && filter_operator && filter_right,
				}"
				aria-hidden="true"
			/>
		</div>

		<transition
			enter-active-class="transition ease-out duration-100"
			enter-from-class="transform opacity-0 scale-95"
			enter-to-class="transform opacity-100 scale-100"
			leave-active-class="transition ease-in duration-75"
			leave-from-class="transform opacity-100 scale-100"
			leave-to-class="transform opacity-0 scale-95"
		>
			<div
				v-if="focused && suggestions.length != 0"
				class="absolute top-10 mt-2 max-h-52 w-full origin-top overflow-scroll overflow-x-hidden rounded-md bg-white shadow-md ring-1 ring-black ring-opacity-5 focus:outline-none"
			>
				<div
					v-for="item in suggestions"
					:key="item.label"
					class="suggestion flex cursor-default items-center justify-between rounded-md px-4 py-3 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
					@click.prevent="on_suggestion_select(item)"
				>
					<div class="flex items-center">
						<div class="font-semibold">{{ item.label }}</div>
					</div>
					<div v-if="item.table" class="flex font-light text-slate-400">
						{{ item.table }}&nbsp;&#8226;&nbsp;{{ item.type }}
					</div>
				</div>
			</div>
		</transition>
	</div>
</template>

<script>
import FeatherIcon from 'frappe-ui/src/components/FeatherIcon.vue'

export default {
	components: {
		FeatherIcon,
	},
	props: ['tables', 'should_focus'],
	data() {
		return {
			focused: false,
			input_value: '',
			delimiter: ';',
		}
	},
	mounted() {
		// detect click outside of input
		document.addEventListener('click', (e) => {
			if (
				e.target.closest('.filter-search') ||
				e.target.classList.contains('suggestion')
			) {
				return this.$refs.filter_search?.focus()
			}
			this.focused = false
		})
	},
	resources: {
		column_list() {
			return {
				method: 'analytics.api.get_column_list',
				params: {
					tables: this.tables,
				},
				auto: true,
				onSuccess() {
					this.column_list.forEach((c) => (c.is_left = true))
				},
			}
		},
		operator_list() {
			return {
				method: 'analytics.api.get_operator_list',
				onSuccess() {
					this.operator_list.forEach((o) => (o.is_operator = true))
				},
			}
		},
	},
	computed: {
		column_list() {
			return this.$resources.column_list.data || []
		},
		operator_list() {
			return this.$resources.operator_list.data || []
		},
		placeholder() {
			const [left, operator, right] = this.input_value.split(this.delimiter)
			if (!this.left_selected) {
				return 'Select a column...'
			} else if (this.left_selected && !operator) {
				return 'select an operator...'
			} else if (this.left_selected && this.operator_selected && !right) {
				return 'type a string value...'
			}
		},
		left_selected() {
			const regex = RegExp(`${this.delimiter}`, 'g')
			return (this.input_value.match(regex) || []).length > 0
		},
		operator_selected() {
			const regex = RegExp(`${this.delimiter}`, 'g')
			return (this.input_value.match(regex) || []).length > 1
		},
		filter_left() {
			return this.input_value.split(this.delimiter)[0]
		},
		filter_operator() {
			return (this.input_value.split(this.delimiter)[1] || '').toLowerCase()
		},
		filter_right() {
			return this.input_value.split(this.delimiter)[2]
		},
		suggestions() {
			const [left, operator, right] = this.input_value.split(this.delimiter)

			if (!this.left_selected) {
				return left
					? this.column_list.filter((c) =>
							c.label.toLowerCase().includes(left.toLowerCase())
					  )
					: this.column_list
			} else if (!this.operator_selected) {
				return operator
					? this.operator_list.filter((o) =>
							o.label.toLowerCase().includes(operator.toLowerCase())
					  )
					: this.operator_list
			} else {
				return []
			}
		},
	},
	methods: {
		on_suggestion_select(suggestion) {
			if (suggestion.is_left) {
				this.$resources.operator_list.submit({ fieldtype: suggestion.type })
				this.input_value = `${suggestion.label}${this.delimiter}`
			} else if (suggestion.is_operator) {
				const operator = suggestion.label.toLowerCase()
				this.input_value = `${this.filter_left}${this.delimiter}${operator}${this.delimiter}`
			}
		},
		on_backspace(e) {
			// delete the previous selection if a delimiter is deleted
			const last_letter = e.target.value.slice(-1)
			if (last_letter && last_letter == this.delimiter) {
				e.stopPropagation()
				e.preventDefault()
				this.input_value = e.target.value
					.split(this.delimiter) // split by delimiter = [left, operator, '']
					.filter((v) => v) // remove empty values = [left, operator]
					.slice(0, -1) // remove last value = [left]
					.map((v) => `${v}${this.delimiter}`) // add delimiter = ['left;']
					.join('') // join by empty string = left;
			}
		},
		on_enter() {
			if (this.filter_left && this.filter_operator && this.filter_right) {
				const left_suggestion = this.column_list.find(
					(c) => c.label.toLowerCase() === this.filter_left.toLowerCase()
				)
				const operator_suggestion = this.operator_list.find(
					(o) => o.label.toLowerCase() === this.filter_operator.toLowerCase()
				)
				this.$emit('filter_selected', {
					left_table: left_suggestion.table,
					left: this.filter_left,
					left_value: left_suggestion.name,
					operator: this.filter_operator,
					operator_value: operator_suggestion.value,
					right: this.filter_right,
				})
				this.input_value = ''
				this.focused = false
				this.$refs.filter_search?.blur()
			}
		},
	},
}
</script>
