<template>
	<td
		v-for="col in $props.columns"
		class="bg-gray-100 px-2.5 py-1.5 first:rounded-l-md last:rounded-r-md"
		scope="col"
	>
		<div class="flex items-center">
			<span class="mr-2 overflow-hidden text-ellipsis whitespace-nowrap">
				{{ col.label }} : {{ col.type }}
			</span>
			<div class="h-6">
				<Popover>
					<template #target="{ togglePopover }">
						<div
							class="cursor-pointer rounded p-1 hover:bg-gray-200"
							@click="togglePopover()"
						>
							<FeatherIcon name="more-horizontal" class="h-4 w-4" />
						</div>
					</template>
					<template #body="{ isOpen, togglePopover }">
						<div
							v-if="isOpen"
							class="flex items-end space-x-2 rounded bg-white px-3 py-2 shadow-md"
						>
							<Input
								class="w-40"
								type="select"
								label="Change Type"
								:options="[
									'String',
									'Integer',
									'Decimal',
									'Text',
									'Datetime',
									'Date',
									'Time',
								]"
								v-model="col.type"
							></Input>
							<Button
								icon="check"
								variant="solid"
								@click="$emit('update-column-type', col) & togglePopover()"
							></Button>
						</div>
					</template>
				</Popover>
			</div>
		</div>
	</td>
</template>

<script setup>
import { ref } from 'vue'
defineEmits(['update-column-type'])
defineProps({ columns: Object })
</script>
