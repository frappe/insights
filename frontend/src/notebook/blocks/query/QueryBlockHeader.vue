<script setup lang="jsx">
import useDataSourceStore from '@/stores/dataSourceStore'
import { copyToClipboard } from '@/utils'
import { debounce } from 'frappe-ui'
import { computed, inject, ref } from 'vue'
import { useRouter } from 'vue-router'
import ResizeableInput from './builder/ResizeableInput.vue'

const state = inject('state')
const debouncedUpdateTitle = debounce(async (title) => {
	await state.query.setValue.submit({ title })
	state.query.doc.title = title
}, 1500)

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
			page.addQuery(state.query.doc.is_native_query ? 'query-editor' : 'query-builder', name)
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
	state.query.updateDoc({ data_source: sourceName }).then(() => {
		$notify({
			title: 'Data source updated',
			variant: 'success',
		})
		state.query.doc.data_source = sourceName
	})
}
</script>

<template>
	<div class="flex h-9 items-center justify-between rounded-t-lg pl-3 pr-1 text-base">
		<div class="flex items-center font-mono">
			<ResizeableInput
				v-model="state.query.doc.title"
				class="-ml-2 cursor-text"
				@update:model-value="debouncedUpdateTitle"
			></ResizeableInput>
			<p class="text-gray-600">({{ state.query.doc.name }})</p>
			<p
				class="ml-2.5 h-1.5 w-1.5 rounded-full"
				:class="[!state.query.unsaved ? 'hidden' : 'bg-orange-500']"
			></p>
		</div>
		<div class="flex items-center space-x-2">
			<Dropdown
				v-if="!state.query.doc.is_assisted_query"
				:button="{
					iconLeft: 'database',
					variant: 'outline',
					label: currentSource?.title || 'Select data source',
				}"
				:options="dataSourceOptions"
			/>
			<Button
				variant="outline"
				icon="play"
				label="Execute"
				:onClick="() => state.query.execute() || (state.minimizeResult = false)"
				:loading="state.query.executing"
			/>
			<Button
				variant="outline"
				:icon="state.minimizeResult ? 'maximize-2' : 'minimize-2'"
				:label="state.minimizeResult ? 'Show Results' : 'Hide Results'"
				:onClick="() => (state.minimizeResult = !state.minimizeResult)"
			/>
			<Button
				variant="outline"
				label="Duplicate"
				icon="copy"
				:onClick="duplicateQuery"
				:loading="state.query.duplicating"
			/>
			<Button
				v-if="!state.query.doc.is_native_query && state.query.doc.sql"
				variant="outline"
				label="View SQL"
				icon="code"
				:onClick="() => (show_sql_dialog = true)"
			/>
			<Button
				variant="outline"
				icon="trash"
				label="Delete"
				:onClick="state.removeQuery"
				:loading="state.query.deleting"
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
					variant="outline"
					class="absolute bottom-2 right-2"
					@click="copyToClipboard(state.query.doc.sql)"
				></Button>
			</div>
		</template>
	</Dialog>
</template>
