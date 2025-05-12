<script setup lang="ts">
import { PlayIcon, Scroll } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import { Query } from '../query'
import ViewSQLDialog from './ViewSQLDialog.vue'
import { useTimeAgo } from '@vueuse/core'

const query = inject('query') as Query

const showViewSQLDialog = ref(false)

const actions = [
	// {
	// 	label: 'Manage Columns',
	// 	icon: Columns,
	// },
	{
		label: 'View SQL',
		icon: Scroll,
		onClick: () => (showViewSQLDialog.value = true),
	},
	{
		label: 'Execute',
		icon: PlayIcon,
		onClick: () => query.execute(),
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
			<template v-for="(action, idx) in actions" :key="idx">
				<Button
					:variant="'ghost'"
					:label="action.label"
					@click="action.onClick"
					class="!h-6 !gap-1.5 bg-white !px-2 text-xs shadow"
				>
					<template #prefix>
						<component
							:is="action.icon"
							class="h-3 w-3 text-gray-700"
							stroke-width="1.5"
						/>
					</template>
				</Button>
			</template>
		</div>
	</div>

	<ViewSQLDialog v-if="showViewSQLDialog" v-model="showViewSQLDialog" />
</template>
