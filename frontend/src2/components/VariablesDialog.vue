<script setup lang="ts">
import { Plus } from 'lucide-vue-next'
import { computed } from 'vue'
import type { QueryVariable } from '../types/workbook.types'

interface Props {
	show: boolean
	variables: QueryVariable[]
}

interface Emits {
	(e: 'update:show', value: boolean): void
	(e: 'update:variables', value: QueryVariable[]): void
	(e: 'save', value: QueryVariable[]): void
}

const emit = defineEmits<Emits>()
const props = defineProps<Props>()

const show = computed({
	get: () => props.show,
	set: (value: boolean) => emit('update:show', value),
})

const variables = computed({
	get: () => props.variables || [],
	set: (value: QueryVariable[]) => emit('update:variables', value),
})

function addVariable() {
	const newVariables = [...variables.value]
	newVariables.push({
		variable_name: '',
		variable_value: '',
	})
	variables.value = newVariables
}

function removeVariable(index: number) {
	const newVariables = [...variables.value]
	newVariables.splice(index, 1)
	variables.value = newVariables
}

function saveVariables() {
	const validVariables = variables.value.filter((v) => v.variable_name.trim().length > 0)
	emit('save', validVariables)
}
</script>

<template>
	<Dialog
		:modelValue="show"
		@update:modelValue="show = $event"
		:options="{ title: 'Variables', size: 'lg' }"
	>
		<template #body>
			<div class="bg-white px-4 pb-6 pt-5 sm:px-6">
				<div class="flex items-center justify-between pb-4">
					<h3 class="text-2xl font-semibold leading-6 text-gray-900">Variables</h3>
					<Button variant="ghost" @click="show = false" icon="x" size="md" />
				</div>

				<p class="mb-5 text-p-base text-gray-600">
					Variables are used to store sensitive information such as API keys and
					credentials. They can be referenced and combined in your script just like any
					other variable. For eg.
					<br />
					<code class="rounded bg-gray-100 px-1 my-1 py-0.5 text-p-sm text-gray-800">
						formatted_api_key = f'token {api_key}:{api_secret}'
					</code>
				</p>

				<div class="flex flex-col overflow-hidden">
					<div class="relative flex max-h-[20rem] flex-col overflow-y-auto">
						<div
							class="sticky top-0 flex gap-x-2 border-b bg-white py-2 text-p-sm font-medium text-gray-600"
						>
							<div class="flex flex-1 flex-shrink-0 px-2">Name</div>
							<div class="flex flex-1 flex-shrink-0 px-2">Value</div>
							<div class="flex w-10"></div>
						</div>

						<div
							v-for="(variable, index) in variables"
							:key="index"
							class="flex gap-x-2 border-b border-gray-100 py-1"
						>
							<div class="flex flex-1 flex-shrink-0">
								<input
									class="w-full rounded-sm border-none bg-transparent px-2 py-2 text-base focus:bg-gray-100 focus:outline-none focus:ring-0"
									type="text"
									v-model="variable.variable_name"
									placeholder="e.g. api_key"
								/>
							</div>
							<div class="flex flex-1 flex-shrink-0">
								<input
									type="password"
									class="w-full rounded-sm border-none bg-transparent px-2 py-2 text-base focus:bg-gray-100 focus:outline-none focus:ring-0"
									v-model="variable.variable_value"
									placeholder="**********************"
								/>
							</div>
							<div class="flex w-10 justify-end">
								<Button
									variant="ghost"
									icon="x"
									size="sm"
									@click="removeVariable(index)"
								/>
							</div>
						</div>

						<div v-if="variables.length === 0" class="flex justify-center py-8">
							<span class="text-p-sm text-gray-400">No variables added</span>
						</div>
					</div>

					<div class="mt-4 flex justify-between">
						<Button variant="outline" @click="addVariable">
							<template #prefix>
								<Plus class="h-4 w-4" />
							</template>
							Add Variable
						</Button>
						<Button variant="solid" @click="saveVariables"> Save Variables </Button>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
