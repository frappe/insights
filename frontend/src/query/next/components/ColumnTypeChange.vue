<script setup lang="ts">
import { COLUMN_TYPES, fieldtypesToIcon } from '@/utils'
import { ChevronRight } from 'lucide-vue-next'
import { QueryPipelineResultColumn } from '../useQueryPipeline'

const emit = defineEmits({
	typeChange: (newType: ColumnType) => true,
})
const props = defineProps<{ column: QueryPipelineResultColumn }>()
</script>

<template>
	<Popover placement="right-start">
		<template #target="{ togglePopover, isOpen }">
			<Button
				variant="ghost"
				@click="togglePopover"
				class="w-full !justify-start"
				:class="{ ' !bg-gray-100': isOpen }"
			>
				<template #icon>
					<div class="flex w-full items-center gap-2 px-1.5 text-base">
						<component
							:is="fieldtypesToIcon[props.column.type]"
							class="h-4 w-4 text-gray-700"
						/>
						<div class="flex flex-1 items-center justify-between">
							<span class="truncate">Change Type</span>
							<ChevronRight class="h-4 w-4" />
						</div>
					</div>
				</template>
			</Button>
		</template>
		<template #body-main="{ togglePopover }">
			<div class="flex min-w-[10rem] flex-col p-1.5">
				<Button
					v-for="type in COLUMN_TYPES"
					:key="type.value"
					variant="ghost"
					class="w-full !justify-start"
					@click=";[togglePopover(), emit('typeChange', type.value as ColumnType)]"
				>
					<template #prefix>
						<component
							:is="fieldtypesToIcon[props.column.type]"
							class="h-4 w-4 text-gray-700"
						/>
					</template>
					<span class="truncate">{{ type.label }}</span>
				</Button>
			</div>
		</template>
	</Popover>
</template>
