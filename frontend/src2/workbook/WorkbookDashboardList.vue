<script setup lang="ts">
import { Plus, Table2, X } from 'lucide-vue-next'
import { inject } from 'vue'
import { Workbook, workbookKey } from './workbook'

const workbook = inject(workbookKey) as Workbook
</script>

<template>
	<div class="flex flex-col gap-2 px-2.5 py-2">
		<div class="flex h-6 items-center justify-between">
			<div class="flex items-center gap-1">
				<div class="text-[11px] uppercase">Dashboards</div>
			</div>
			<div>
				<button
					class="cursor-pointer rounded p-1 transition-colors hover:bg-gray-100"
					@click="workbook.addDashboard()"
				>
					<Tooltip text="New Dashboard" :hover-delay="0.1">
						<Plus class="h-4 w-4 text-gray-700" stroke-width="1.5" />
					</Tooltip>
				</button>
			</div>
		</div>
		<div
			v-if="!workbook.doc.dashboards.length"
			class="flex h-12 flex-col items-center justify-center rounded border border-dashed border-gray-300 py-2"
		>
			<div class="text-xs text-gray-500">No dashboards</div>
		</div>
		<div v-else class="flex flex-col">
			<button
				v-for="(row, idx) in workbook.doc.dashboards"
				:key="row.name"
				@click="workbook.setActiveTab('dashboard', row.name)"
				class="group flex w-full cursor-pointer items-center justify-between rounded border border-gray-300 p-0.5 pl-1.5 text-sm transition-all hover:border-gray-400"
				:class="
					workbook.isActiveTab(row.name)
						? 'border-gray-700 hover:border-gray-700'
						: 'border-gray-200'
				"
			>
				<div class="flex gap-1.5">
					<Table2 class="h-4 w-4 text-gray-700" stroke-width="1.5" />
					<p>{{ row.name }}</p>
				</div>
				<button
					class="invisible cursor-pointer rounded p-1 transition-all hover:bg-gray-100 group-hover:visible"
					@click.prevent.stop="workbook.removeDashboard(row.name)"
				>
					<Tooltip text="Delete Dashboard" :hover-delay="0.5">
						<X class="h-4 w-4 text-gray-700" stroke-width="1.5" />
					</Tooltip>
				</button>
			</button>
		</div>
	</div>
</template>
