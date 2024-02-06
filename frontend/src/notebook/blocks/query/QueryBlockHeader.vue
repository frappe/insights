<script setup lang="jsx">
import ResizeableInput from '@/components/ResizeableInput.vue'
import useDataSourceStore from '@/stores/dataSourceStore'
import { copyToClipboard } from '@/utils'
import { debounce } from 'frappe-ui'
import { Component as ComponentIcon } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import { useRouter } from 'vue-router'
import QueryDataSourceSelector from '@/query/QueryDataSourceSelector.vue'

const state = inject('state')
const debouncedUpdateTitle = debounce((title) => state.query.updateTitle(title), 1500)

const show_sql_dialog = ref(false)
const formattedSQL = computed(() => {
	return state.query.doc.sql
		.replaceAll('\n', '<br>')
		.replaceAll('      ', '&ensp;&ensp;&ensp;&ensp;')
})

const page = inject('page')
const router = useRouter()
function duplicateQuery() {
	state.query.duplicate().then((name) => {
		if (page?.addQuery) {
			page.addQuery('query-editor', name)
		} else {
			router.push(`/query/build/${name}`)
		}
	})
}

const sources = useDataSourceStore()

const SourceOption = (props) => {
	return (
		<div
			class="group flex w-full cursor-pointer items-center justify-between rounded-md px-2 py-2 text-sm hover:bg-gray-100"
			onClick={() => changeDataSource(props.name)}
		>
			<span>{props.label}</span>
			<FeatherIcon v-show={props.active} name="check" class="h-4 w-4 text-gray-600" />
		</div>
	)
}
const currentSource = computed(() => {
	return sources.list.find((source) => source.name === state.query.doc.data_source)
})
const dataSourceOptions = computed(() => {
	return sources.list.map((source) => ({
		component: (props) => (
			<SourceOption
				name={source.name}
				label={source.title}
				active={source.name === state.query.doc.data_source}
			/>
		),
	}))
})

function changeDataSource(sourceName) {
	state.query.changeDataSource(sourceName).then(() => {
		$notify({
			title: 'Data source updated',
			variant: 'success',
		})
		state.query.doc.data_source = sourceName
	})
}
</script>

<template>
	<div class="flex items-center justify-between rounded-t-lg p-1 pl-3 text-base">
		<div class="flex items-center font-mono text-sm">
			<div v-if="state.query.doc.is_stored" class="mr-1">
				<ComponentIcon class="h-3 w-3 text-gray-600" fill="currentColor" />
			</div>
			<ResizeableInput
				v-model="state.query.doc.title"
				class="-ml-2 cursor-text"
				@update:model-value="debouncedUpdateTitle"
			></ResizeableInput>
			<p class="text-gray-600">({{ state.query.doc.name }})</p>
		</div>
		<div class="flex items-center space-x-1">
			<QueryDataSourceSelector></QueryDataSourceSelector>
			<Dropdown
				:button="{
					icon: 'more-vertical',
					variant: 'outline',
				}"
				:options="[
					{
						label: state.minimizeResult ? 'Show Results' : 'Hide Results',
						icon: state.minimizeResult ? 'maximize-2' : 'minimize-2',
						onClick: () => (state.minimizeResult = !state.minimizeResult),
					},
					{
						label: 'Duplicate',
						icon: 'copy',
						onClick: duplicateQuery,
						loading: state.query.duplicating,
					},
					{
						label: 'View SQL',
						icon: 'code',
						onClick: () => (show_sql_dialog = true),
						loading: state.query.duplicating,
					},
					{
						label: 'Delete',
						icon: 'trash',
						onClick: state.removeQuery,
						loading: state.query.deleting,
					},
				]"
			/>
		</div>
	</div>

	<Dialog
		:options="{ title: 'Generated SQL', size: '3xl' }"
		v-model="show_sql_dialog"
		:dismissable="true"
	>
		<template #body-content>
			<div class="relative">
				<p
					class="rounded border bg-gray-100 p-2 text-base text-gray-600"
					style="font-family: 'Fira Code'"
					v-html="formattedSQL"
				></p>
				<Button
					icon="copy"
					variant="ghost"
					class="absolute bottom-2 right-2"
					@click="copyToClipboard(state.query.doc.sql)"
				></Button>
			</div>
		</template>
	</Dialog>
</template>
