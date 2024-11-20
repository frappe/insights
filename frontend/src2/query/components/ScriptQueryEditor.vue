<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'
import { LoadingIndicator } from 'frappe-ui'
import { Play, RefreshCw, Wand2 } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import Code from '../../components/Code.vue'
import DataTable from '../../components/DataTable.vue'
import { Query } from '../query'
import ContentEditable from '../../components/ContentEditable.vue'

const query = inject<Query>('query')!

const operation = query.getCodeOperation()
const code = ref(operation ? operation.code : '')
function execute() {
	query.setCode({ code: code.value })
}

const columns = computed(() => query.result.columns)
const rows = computed(() => query.result.formattedRows)
const previewRowCount = computed(() => query.result.rows.length.toLocaleString())
const totalRowCount = computed(() =>
	query.result.totalRowCount ? query.result.totalRowCount.toLocaleString() : ''
)

const exampleCode = `# This is an example script that fetches data from a URL and logs the data to the script log

def fetch_data_from_url():
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
	<div class="flex flex-1 flex-col gap-4 overflow-hidden p-4">
		<div class="relative flex h-[55%] w-full flex-col rounded border">
			<div class="flex flex-shrink-0 items-center gap-1 border-b p-1">
				<ContentEditable
					class="flex h-7 cursor-text items-center justify-center rounded bg-white px-2 text-base text-gray-800 focus-visible:ring-1 focus-visible:ring-gray-600"
					v-model="query.doc.title"
					placeholder="Untitled Dashboard"
				></ContentEditable>
			</div>
			<div class="flex-1 overflow-hidden">
				<Code v-model="code" language="python" :placeholder="exampleCode" />
			</div>
			<div class="flex flex-shrink-0 gap-1 border-t p-1">
				<Button @click="execute" label="Run">
					<template #prefix>
						<Play class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</div>
		</div>
		<div
			v-show="query.result.executedSQL"
			class="tnum flex flex-shrink-0 items-center gap-2 text-sm text-gray-600"
		>
			<div class="h-2 w-2 rounded-full bg-green-500"></div>
			<div>
				<span v-if="query.result.timeTaken == -1"> Fetched from cache </span>
				<span v-else> Fetched in {{ query.result.timeTaken }}s </span>
				<span> {{ useTimeAgo(query.result.lastExecutedAt).value }} </span>
			</div>
		</div>
		<div class="relative flex w-full flex-1 flex-col overflow-hidden rounded border">
			<div
				v-if="query.executing"
				class="absolute top-10 z-10 flex w-full items-center justify-center rounded bg-gray-50/30 backdrop-blur-sm"
			>
				<LoadingIndicator class="h-8 w-8 text-gray-700" />
			</div>

			<DataTable :columns="columns" :rows="rows" :on-export="query.downloadResults">
				<template #footer-left>
					<div class="tnum flex items-center gap-2 text-sm text-gray-600">
						<span> Showing {{ previewRowCount }} of </span>
						<span v-if="!totalRowCount" class="inline-block">
							<Tooltip text="Load Count">
								<RefreshCw
									v-if="!query.fetchingCount"
									class="h-3.5 w-3.5 cursor-pointer transition-all hover:text-gray-800"
									stroke-width="1.5"
									@click="query.fetchResultCount"
								/>
								<LoadingIndicator v-else class="h-3.5 w-3.5 text-gray-600" />
							</Tooltip>
						</span>
						<span v-else> {{ totalRowCount }} </span>
						rows
					</div>
				</template>
			</DataTable>
		</div>
	</div>
</template>
