<script setup lang="ts">
import Code from '@/components/Controls/Code.vue'
import { copyToClipboard } from '@/utils'
import { computed, inject } from 'vue'
import { Query } from './useQuery'

const showDialog = defineModel()

const query = inject('query') as Query
const formattedSQL = computed(() => {
	return query.result.executedSQL
	// .replace(/\n/g, '<br>')
	// .replace(/      /g, '&ensp;&ensp;&ensp;&ensp;')
})
</script>

<template>
	<Dialog
		v-model="showDialog"
		:options="{ title: 'Generated SQL', size: '3xl' }"
		:dismissable="true"
	>
		<template #body-content>
			<div class="relative">
				<div class="max-h-[50vh] overflow-y-auto rounded border text-base">
					<Code
						language="sql"
						:model-value="query.result.executedSQL"
						:read-only="true"
						:hide-line-numbers="true"
					/>
				</div>
				<Button
					icon="copy"
					variant="outline"
					class="absolute bottom-2 right-2"
					@click="copyToClipboard(query.result.executedSQL)"
				></Button>
			</div>
		</template>
	</Dialog>
</template>
