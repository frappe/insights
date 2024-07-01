<script setup lang="ts">
import { ChevronRight, TextCursorInput } from 'lucide-vue-next'
import { ref } from 'vue'
import { QueryResultColumn } from '../../types/query.types'

const emit = defineEmits({
	rename: (newName: string) => true,
})
const props = defineProps<{ column: QueryResultColumn }>()
const newName = ref('')
function onRename() {
	emit('rename', newName.value)
	newName.value = ''
}
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
						<TextCursorInput class="h-4 w-4 flex-shrink-0" />
						<div class="flex flex-1 items-center justify-between">
							<span class="truncate">Rename</span>
							<ChevronRight class="h-4 w-4" />
						</div>
					</div>
				</template>
			</Button>
		</template>
		<template #body-main="{ togglePopover }">
			<div class="flex flex-col gap-2 px-2.5 py-2">
				<FormControl v-model="newName" label="New Column Name" />
				<div class="flex justify-end gap-1">
					<Button @click="togglePopover" icon="x"></Button>
					<Button variant="solid" icon="check" @click=";[onRename(), togglePopover()]">
					</Button>
				</div>
			</div>
		</template>
	</Popover>
</template>
