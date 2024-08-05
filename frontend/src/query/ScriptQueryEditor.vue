<script setup>
import Code from '@/components/Controls/Code.vue'
import { useStorage } from '@vueuse/core'
import { Braces, Bug } from 'lucide-vue-next'
import { computed, inject, ref, watch } from 'vue'
import VariablesDialog from './VariablesDialog.vue'
import ResultSection from './ResultSection.vue'

const query = inject('query')
const script = ref(query.doc.script)
watch(
	() => query.doc.script,
	(value) => (script.value = value)
)
const executing = ref(false)
async function onExecuteQuery() {
	if (executing.value) return
	executing.value = true
	try {
		await query.updateScript(script.value)
		await query.execute()
	} finally {
		executing.value = false
	}
}

const showVariablesDialog = ref(false)
function handleSaveVariables(variables) {
	query.updateScriptVariables(variables)
	showVariablesDialog.value = false
}

const showLogs = useStorage(`insights:query-${query.doc.name}-show-logs`, false)
const scriptLogs = computed(() => query.doc.script_log?.split('\n')?.slice(1))
const showHelp = ref(false)
const exampleCode = `def fetch_data_from_url():
		# URL of the CSV file
		csv_url = "https://example.com/data.csv"

		try:
				# Read data from the CSV file into a Pandas DataFrame
				df = pandas.read_csv(csv_url)

				# use the log function to log messages to the script log
				log(df)

				# return the DataFrame
				return df

		except Exception as e:
				log("An error occurred:", str(e))
				return None

# Call the function to execute the script and
# then convert the data into a Pandas DataFrame or a List of lists with first row as column names
results = fetch_data_from_url()`
</script>

<template>
	<div class="flex h-full w-full flex-col pt-2">
		<div class="flex-shrink-0 uppercase leading-7 tracking-wide text-gray-600">
			Script Query
		</div>
		<div class="flex flex-1 flex-shrink-0 overflow-hidden rounded border">
			<div class="relative flex flex-1 flex-col overflow-y-auto">
				<Code language="python" v-model="script" placeholder="Enter your script here...">
				</Code>
				<div class="sticky bottom-0 flex justify-between border-t bg-white p-2">
					<div class="flex gap-2">
						<Button variant="outline" icon="help-circle" @click="showHelp = true" />
						<Button
							variant="outline"
							@click="showVariablesDialog = !showVariablesDialog"
						>
							<template #icon>
								<Braces class="h-4 w-4" />
							</template>
						</Button>
						<Button variant="outline" @click="showLogs = !showLogs">
							<template #icon>
								<Bug class="h-4 w-4" />
							</template>
						</Button>
						<Button
							variant="solid"
							icon="play"
							@click="onExecuteQuery"
							:loading="executing"
						>
						</Button>
					</div>
				</div>
			</div>
			<transition
				tag="div"
				name="slide"
				enter-active-class="transition ease-out duration-200"
				enter-from-class="transform translate-x-full opacity-0"
				enter-to-class="transform translate-x-0 opacity-100"
				leave-active-class="transition ease-in duration-200"
				leave-from-class="transform translate-x-0"
				leave-to-class="transform translate-x-full"
			>
				<div
					v-if="showLogs"
					class="flex h-full w-[30rem] flex-col overflow-hidden bg-gray-50 p-3"
				>
					<div class="text-sm uppercase tracking-wide text-gray-600">Logs</div>
					<div class="mt-2 flex w-full flex-col gap-2 overflow-y-auto font-mono">
						<div v-for="(log, index) in scriptLogs" :key="index" class="flex gap-2">
							<div class="text-gray-400">[{{ index + 1 }}]</div>
							<div class="text-gray-500">{{ log }}</div>
						</div>
					</div>
				</div>
			</transition>
		</div>
		<div class="flex w-full flex-1 flex-shrink-0 overflow-hidden py-4">
			<ResultSection></ResultSection>
		</div>
	</div>

	<VariablesDialog
		v-model:show="showVariablesDialog"
		v-model:variables="query.doc.variables"
		@save="handleSaveVariables"
	/>

	<Dialog
		v-model="showHelp"
		:options="{
			title: 'Help',
			size: '3xl',
		}"
	>
		<template #body-content>
			<div class="flex w-full flex-col gap-2 text-base leading-5">
				<div class="">
					In the Script Query interface, you can write custom Python scripts to query the
					database and retrieve data as a Pandas DataFrame. You can also fetch data from
					external sources using Pandas functions
				</div>
				<div>
					For detailed information about these functions and how to use them, please refer
					to
					<a
						class="text-blue-500 underline"
						href="https://frappeframework.com/docs/user/en/desk/scripting/script-api"
					>
						Frappe Framework's Script API
					</a>
				</div>
				<div class="">
					Example script to read data from a CSV file hosted on a URL and create a Pandas
					DataFrame:
				</div>
				<div class="rounded bg-gray-50 text-sm">
					<Code :readOnly="true" language="python" :model-value="exampleCode"> </Code>
				</div>
			</div>
		</template>
	</Dialog>
</template>
