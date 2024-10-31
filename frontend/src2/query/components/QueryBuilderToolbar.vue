<script setup lang="ts">
import { Tooltip } from 'frappe-ui'
import { ArrowLeftRight, CodeIcon, Columns, Download, PlayIcon } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import ContentEditable from '../../components/ContentEditable.vue'
import { Query } from '../query'
import ViewSQLDialog from './ViewSQLDialog.vue'

const query = inject('query') as Query

const showViewSQLDialog = ref(false)

const actions = [
	{
		type: 'separator',
	},
	// {
	// 	label: 'Manage Columns',
	// 	icon: Columns,
	// },
	{
		label: 'View SQL',
		icon: CodeIcon,
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
	<div class="flex w-full flex-shrink-0 items-center justify-between bg-gray-50 p-2">
		<div class="flex w-full items-center gap-2">
			<template v-for="(action, idx) in actions" :key="idx">
				<div v-if="action.type === 'separator'" class="h-7 flex-1"></div>
				<Tooltip v-else placement="top" :hover-delay="0.1" :text="action.label">
					<Button
						:variant="'ghost'"
						@click="action.onClick"
						class="h-7 w-7 bg-white shadow"
					>
						<template #icon>
							<component
								:is="action.icon"
								class="h-4 w-4 text-gray-700"
								stroke-width="1.5"
							/>
						</template>
					</Button>
				</Tooltip>
			</template>
		</div>
	</div>

	<ViewSQLDialog v-if="showViewSQLDialog" v-model="showViewSQLDialog" />
</template>
