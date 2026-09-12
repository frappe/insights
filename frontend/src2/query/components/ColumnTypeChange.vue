<script setup lang="ts">
import { COLUMN_TYPES } from '../../helpers/constants'
import { ColumnDataType } from '../../types/query.types'
import DataTypeIcon from './DataTypeIcon.vue'

const modelValue = defineModel<ColumnDataType>({
	required: true,
})
function onTypeChange(newType: ColumnDataType, togglePopover: () => void) {
	modelValue.value = newType
	togglePopover()
}
</script>

<template>
	<Popover side="bottom" align="start">
		<template #trigger="{ open }">
			<Button variant="ghost" class="rounded-none" :class="open ? '!bg-surface-gray-2' : ''">
				<template #icon>
					<DataTypeIcon :columnType="modelValue" />
				</template>
			</Button>
		</template>
		<template #default="{ toggle: togglePopover, open }">
			<div v-if="open" class="flex min-w-[10rem] flex-col p-1.5">
				<Button
					v-for="type in COLUMN_TYPES"
					:key="type.value"
					variant="ghost"
					class="w-full !justify-start"
					@click="onTypeChange(type.value as ColumnDataType, togglePopover)"
				>
					<template #prefix>
						<DataTypeIcon :columnType="type.value as ColumnDataType" />
					</template>
					<span class="truncate">{{ type.label }}</span>
				</Button>
			</div>
		</template>
	</Popover>
</template>
