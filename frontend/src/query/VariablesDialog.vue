<script setup>
import { computed } from 'vue'

const emit = defineEmits(['update:show', 'update:variables', 'save'])
const props = defineProps({ show: Boolean, variables: Array })

const show = computed({
	get: () => props.show,
	set: (value) => emit('update:show', value),
})

const variables = computed({
	get: () => props.variables,
	set: (value) => emit('update:variables', value),
})
</script>

<template>
	<Dialog v-model="show" :options="{ title: 'Variables' }">
		<template #body-content>
			<p class="-mt-4 mb-5 text-base text-gray-600">
				Variables are used to store sensitive information such as API keys and credentials.
				They can be referenced in your script just like any other variable. For eg.:
				<code class="text-sm text-gray-800">print(api_key)</code>
			</p>
			<div class="flex flex-col overflow-hidden">
				<div class="relative flex max-h-[10rem] flex-col overflow-y-auto">
					<div
						class="sticky top-0 flex gap-x-2 border-b py-2 text-sm uppercase text-gray-600"
					>
						<div class="flex flex-1 flex-shrink-0 px-2">Name</div>
						<div class="flex flex-1 flex-shrink-0 px-2">Value</div>
						<div class="flex w-10"></div>
					</div>
					<div class="flex gap-x-2" v-for="(variable, index) in variables" :key="index">
						<div class="flex flex-1 flex-shrink-0">
							<input
								class="w-full rounded-sm border-none bg-transparent px-2 py-2 text-base focus:bg-gray-100 focus:outline-none focus:ring-0"
								type="text"
								v-model="variable.variable_name"
								placeholder="eg. api_key"
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
							<Button variant="ghost" icon="x" @click="variables.splice(index, 1)" />
						</div>
					</div>
					<div v-if="variables?.length === 0" class="flex justify-center py-4">
						<span class="text-sm text-gray-400">No variables</span>
					</div>
				</div>
				<div class="mt-4 flex justify-between">
					<Button
						variant="subtle"
						@click="
							variables.push({
								variable_name: '',
								variable_type: 'text',
								variable_value: '',
							})
						"
					>
						<span class="text-sm">Add Variable</span>
					</Button>
					<Button variant="solid" label="Save" @click="$emit('save', variables)" />
				</div>
			</div>
		</template>
	</Dialog>
</template>
