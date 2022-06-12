<template>
	<div class="mx-4 mb-4 flex flex-1 flex-col">
		<!-- Picker -->
		<div v-if="!editing_table" class="flex flex-1 flex-col">
			<div v-if="adding_table" class="mb-4 flex flex-shrink-0">
				<Autocomplete
					ref="table_search"
					v-model="new_table"
					:options="new_table_options"
					placeholder="Select a table..."
					@selectOption="add_table"
				/>
			</div>
			<div v-else-if="!adding_table" class="mb-4 flex items-center justify-between">
				<div class="text-lg font-medium">Tables</div>
				<Button icon="plus" @click="adding_table = true"></Button>
			</div>
			<div
				v-if="tables.length == 0"
				class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
			>
				<p>No tables selected</p>
			</div>
			<div v-else class="flex flex-1 select-none flex-col divide-y">
				<div
					v-for="(table, idx) in tables"
					:key="idx"
					class="-mx-1 flex h-10 cursor-pointer items-center justify-between space-x-8 px-2 text-base text-gray-600 hover:bg-gray-50"
					@click.prevent.stop="editing_table = table"
				>
					<div class="flex items-center space-x-2">
						<FeatherIcon name="layout" class="h-[14px] w-[14px] text-gray-500" />
						<div class="text-base font-medium">{{ table.label }}</div>
						<div v-if="table.join" class="text-gray-500">
							<JoinLeftIcon v-if="table.join.type.value == 'left'" />
							<JoinRightIcon v-if="table.join.type.value == 'right'" />
							<JoinInnerIcon v-if="table.join.type.value == 'inner'" />
							<JoinFullIcon v-if="table.join.type.value == 'full_outer'" />
						</div>
						<div v-if="table.join" class="text-base font-medium">{{ table.join.with.label }}</div>
					</div>
					<div
						class="flex items-center px-1 py-0.5 text-gray-500 hover:text-gray-600"
						@click.prevent.stop="remove_table(table)"
					>
						<FeatherIcon name="x" class="h-3 w-3" />
					</div>
				</div>
			</div>
		</div>
		<!-- Editor -->
		<div v-else>
			<div class="mb-4 flex h-7 items-center">
				<Button icon="chevron-left" class="mr-2" @click="editing_table = null"> </Button>
				<div class="text-lg font-medium">Join - {{ editing_table.label }}</div>
			</div>
			<div class="flex flex-col space-y-3">
				<div class="flex flex-col space-y-3">
					<div class="space-y-1 text-sm text-gray-600">
						<div class="font-light">Type</div>
						<Autocomplete v-model="join.type" :options="join_type_options" placeholder="Select a type..." />
					</div>
					<div class="space-y-1 text-sm text-gray-600">
						<div class="font-light">With</div>
						<Autocomplete
							v-model="join.with"
							:options="join_table_options"
							placeholder="Select a table..."
							@selectOption="on_join_table_select"
						/>
					</div>
					<div class="space-y-1 text-sm text-gray-600">
						<div class="font-light">On</div>
						<Autocomplete v-model="join.key" :options="join_key_options" placeholder="Select a key..." />
					</div>
				</div>
				<div class="flex justify-end space-x-2">
					<Button :disabled="!editing_table.join" @click="clear_join"> Clear </Button>
					<Button appearance="primary" :disabled="!join.with || !join.key || !join.type" @click="apply_join">
						Apply
					</Button>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
import JoinLeftIcon from '@/components/Icons/JoinLeftIcon.vue'
import JoinRightIcon from '@/components/Icons/JoinRightIcon.vue'
import JoinInnerIcon from '@/components/Icons/JoinInnerIcon.vue'
import JoinFullIcon from '@/components/Icons/JoinFullIcon.vue'
import Autocomplete from '@/components/Autocomplete.vue'
import TableSearch from '@/components/Query/TableSearch.vue'

import { inject } from 'vue'
import { isEmptyObj } from '@/utils/utils'

export default {
	name: 'TablePicker',
	setup() {
		const query = inject('query')
		return {
			query: query.resource,
		}
	},
	components: {
		JoinLeftIcon,
		JoinRightIcon,
		JoinInnerIcon,
		JoinFullIcon,
		Autocomplete,
		TableSearch,
	},
	data() {
		return {
			new_table: {},
			adding_table: false,
			joining_table: true,
			editing_table: null,
			join: {
				with: {},
				key: {},
				type: {},
			},
		}
	},
	watch: {
		adding_table(newValue) {
			if (newValue) {
				this.query.get_all_tables.fetch(
					{},
					{
						onSuccess: () => {
							this.$refs.table_search.input.el.focus()
						},
					}
				)
			} else {
				this.new_table = {}
			}
		},
		editing_table(table) {
			this.join = {
				with: {},
				key: {},
				type: {},
			}
			if (table) {
				if (table.join) {
					this.join.with = table.join.with
					this.join.key = table.join.key
					this.join.type = table.join.type
				}
				this.query.get_join_options.submit({ table })
			}
		},
	},
	computed: {
		tables() {
			return this.query.doc.tables.map((table) => {
				return {
					...table,
					join: table.join ? JSON.parse(table.join) : null,
				}
			})
		},
		new_table_options() {
			const tables = this.query.get_all_tables?.data?.message || []
			return tables.map((table) => ({
				...table,
				value: table.table,
			}))
		},
		join_options() {
			return this.query.get_join_options.data?.message || []
		},
		join_table_options() {
			return this.join_options.map(({ label, table }) => ({ label, value: table }))
		},
		join_key_options() {
			return !isEmptyObj(this.join.with)
				? this.join_options
						.filter(({ table }) => {
							return table == this.join.with.value
						})
						.map(({ key }) => ({
							label: key,
							value: key,
						}))
				: []
		},
		join_type_options() {
			return [
				{ label: 'Inner', value: 'inner' },
				{ label: 'Left', value: 'left' },
				{ label: 'Right', value: 'right' },
				{ label: 'Full', value: 'full_outer' },
			]
		},
	},
	methods: {
		on_join_table_select(option) {
			this.join.with = option
			this.join.key = {}
			if (this.join_key_options.length == 1) {
				this.join.key = this.join_key_options[0]
			}
		},
		apply_join() {
			this.editing_table.join = this.join
			this.query.update_table.submit({
				table: this.editing_table,
			})
			this.editing_table = null
		},
		clear_join() {
			this.editing_table.join = ''
			this.query.update_table.submit({
				table: this.editing_table,
			})
			this.editing_table = null
		},
		add_table(table) {
			this.query.add_table.submit({ table })
			this.adding_table = false
		},
		remove_table(table) {
			this.query.remove_table.submit({ table })
		},
	},
}
</script>
