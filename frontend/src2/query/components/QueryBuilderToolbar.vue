<script setup lang="ts">
import { CodeIcon, PlayIcon, Scroll } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import { Query } from '../query'
import ViewSQLDialog from './ViewSQLDialog.vue'

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
	<div class="flex w-full flex-shrink-0 items-center justify-between bg-white p-2">
		<div
			v-if="query.result.executedSQL"
			class="tnum flex items-center gap-2 px-2 text-sm text-gray-600"
		>
			<div class="h-2 w-2 rounded-full bg-green-500"></div>
			<span v-if="query.result.timeTaken == -1"> Fetched from cache </span>
			<span v-else> Fetched in {{ query.result.timeTaken }} ms </span>
		</div>
		<div class="flex items-center gap-2">
			<template v-for="(action, idx) in actions" :key="idx">
				<Button
					:variant="'ghost'"
					:label="action.label"
					@click="action.onClick"
					class="bg-white text-sm shadow"
				>
					<template #prefix>
						<component
							:is="action.icon"
							class="h-3.5 w-3.5 text-gray-700"
							stroke-width="1.5"
						/>
					</template>
				</Button>
			</template>
		</div>
	</div>

	<ViewSQLDialog v-if="showViewSQLDialog" v-model="showViewSQLDialog" />
</template>
