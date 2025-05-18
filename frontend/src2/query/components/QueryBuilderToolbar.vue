<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'
import { Copy, MoreHorizontal, PlayIcon, Scroll } from 'lucide-vue-next'
import { h, inject, ref } from 'vue'
import { Query } from '../query'
import ViewSQLDialog from './ViewSQLDialog.vue'

const query = inject('query') as Query

const showViewSQLDialog = ref(false)

const moreActions = [
	{
		label: 'View SQL',
		icon: h(Scroll, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
		onClick: () => (showViewSQLDialog.value = true),
	},
	{
		label: 'Copy JSON',
		icon: h(Copy, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
		onClick: () => query.copy(),
	},
	{
		label: 'Force Execute',
		icon: h(PlayIcon, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
		onClick: () => query.execute(undefined, true),
	},
]
</script>

<template>
	<div class="flex w-full flex-shrink-0 items-center justify-between bg-white">
		<div>
			<div
				v-show="query.result.executedSQL"
				class="tnum flex items-center gap-2 text-sm text-gray-600"
			>
				<div class="h-2 w-2 rounded-full bg-green-500"></div>
				<div>
					<span v-if="query.result.timeTaken == -1"> Fetched from cache </span>
					<span v-else> Fetched in {{ query.result.timeTaken }}s </span>
					<span> {{ useTimeAgo(query.result.lastExecutedAt).value }} </span>
				</div>
			</div>
		</div>
		<div class="flex items-center gap-2">
			<Button
				variant="ghost"
				label="Execute"
				@click="() => query.execute()"
				class="!h-6 !gap-1.5 bg-white !px-2 text-xs shadow"
			>
				<template #prefix>
					<PlayIcon class="h-3 w-3 text-gray-700" stroke-width="1.5" />
				</template>
			</Button>
			<Dropdown placement="right" :options="moreActions">
				<Button variant="ghost" class="!h-6 !gap-1.5 bg-white !px-2 text-xs shadow">
					<template #icon>
						<MoreHorizontal class="h-3 w-3 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</Dropdown>
		</div>
	</div>

	<ViewSQLDialog v-if="showViewSQLDialog" v-model="showViewSQLDialog" />
</template>
