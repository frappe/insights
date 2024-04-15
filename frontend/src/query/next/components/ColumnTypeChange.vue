<script setup lang="ts">
import { COLUMN_TYPES, fieldtypesToIcon } from '@/utils'
import { QueryResultColumn } from '../useQuery'

const emit = defineEmits({
	typeChange: (newType: ColumnDataType) => true,
})
const props = defineProps<{ column: QueryResultColumn }>()
function onTypeChange(newType: ColumnDataType, togglePopover: () => void) {
	emit('typeChange', newType)
	togglePopover()
}
</script>

<template>
	<Popover placement="bottom-start">
		<template #target="{ togglePopover, isOpen }">
			<Button
				variant="ghost"
				class="rounded-sm"
				@click="togglePopover"
				:class="isOpen ? '!bg-gray-100' : ''"
			>
				<template #icon>
					<component
						:is="fieldtypesToIcon[props.column.type]"
						class="h-4 w-4 text-gray-700"
					/>
				</template>
			</Button>
		</template>
		<template #body-main="{ togglePopover, isOpen }">
			<div v-if="isOpen" class="flex min-w-[10rem] flex-col p-1.5">
				<Button
					v-for="type in COLUMN_TYPES"
					:key="type.value"
					variant="ghost"
					class="w-full !justify-start"
					@click="onTypeChange(type.value as ColumnDataType, togglePopover)"
				>
					<template #prefix>
						<component
							:is="fieldtypesToIcon[type.value as ColumnDataType]"
							class="h-4 w-4 text-gray-700"
						/>
					</template>
					<span class="truncate">{{ type.label }}</span>
				</Button>
			</div>
		</template>
	</Popover>
</template>
