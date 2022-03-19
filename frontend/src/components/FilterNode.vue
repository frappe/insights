<template>
	<div class="text-base text-slate-800">
		<div class="flex items-center pb-1 text-sm font-medium">
			<span v-if="level != 1" class="pr-2 font-medium text-slate-300">
				&#8226;
			</span>
			<span
				class="mr-1 flex cursor-pointer items-center rounded border border-slate-200 px-2 py-1"
				@click="$emit('toggle_group_operator', { level })"
			>
				{{ group_operator }}
			</span>
			<span class="text-xs font-light text-slate-400">
				of the following are true
			</span>
		</div>
		<div v-if="conditions && conditions.length" class="flex flex-col">
			<div v-for="(condition, idx) in conditions" :key="idx" class="pl-4">
				<div v-if="condition.group_operator" class="flex items-center pb-1">
					<FilterNode
						:filters="condition"
						@toggle_group_operator="
							(params) => $emit('toggle_group_operator', params)
						"
						@add_filter="(params) => $emit('add_filter', params)"
					/>
				</div>
				<div v-else class="flex cursor-pointer items-center pb-1">
					<div class="pr-2 font-medium text-slate-300">&#8226;</div>
					<div
						class="group relative flex h-10 items-center rounded border border-slate-200 px-3"
					>
						<div class="pr-1 font-medium">{{ condition.left }}</div>
						<div class="pr-1 text-xs font-light">{{ condition.operator }}</div>
						<div class="font-medium text-green-600">{{ condition.right }}</div>
						<div
							class="invisible absolute flex items-center hover:visible group-hover:visible"
							:class="{
								'-right-12': branch_operator == 'or',
								'-right-16': branch_operator == 'and',
							}"
							@click.prevent.stop="
								$emit('add_filter', { idx, level, branch_operator })
							"
						>
							<div
								class="border border-dashed border-slate-200 font-medium text-slate-300"
								:class="{
									'w-4': branch_operator == 'or',
									'w-5': branch_operator == 'and',
								}"
							></div>
							<div
								class="rounded border border-slate-200 px-2 py-1 text-slate-400"
							>
								{{ branch_operator }}
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'FilterNode',
	props: ['filters'],
	computed: {
		level() {
			return this.filters.level || 1
		},
		group_operator() {
			return this.filters.group_operator || 'All'
		},
		branch_operator() {
			return this.group_operator === 'All' ? 'or' : 'and'
		},
		conditions() {
			return this.filters.conditions || []
		},
	},
}
</script>
