<script setup lang="ts">
import { ref, computed } from 'vue'
import { X } from 'lucide-vue-next'
import { Button, FormControl } from 'frappe-ui'
import { EMOJIS } from '../types/emojis'
import { IconName } from '../types/chart.types'
import { iconMap } from '../types/iconMap'

const model = defineModel<string>({ default: '' })

const emit = defineEmits<{
	'update:modelValue': [value: string]
}>()

const searchQuery = ref('')

const filteredIcons = computed(() => {
	if (!searchQuery.value) return EMOJIS
	return EMOJIS.filter((icon) => icon.includes(searchQuery.value))
})

const selectIcon = (icon: IconName) => {
	model.value = icon
	emit('update:modelValue', icon)
	searchQuery.value = ''
}

const clearIcon = () => {
	model.value = ''
	emit('update:modelValue', '')
}
</script>

<template>
	<div class="relative">
		<Popover class="w-full" placement="bottom-start">
			<template #target="{ togglePopover }">
				<Button
					variant="outline"
					class="h-9 w-full justify-center text-center font-normal text-sm"
					@click="togglePopover"
				>
					<component
						v-if="model && iconMap[model as keyof typeof iconMap]"
						:is="iconMap[model as keyof typeof iconMap]"
						class="h-4 w-4 fill-current stroke-0"
					/>
					<span v-else-if="model" class="text-lg leading-none">
						{{ model }}
					</span>
					<span v-else class="truncate text-gray-400">Select Icon</span>
				</Button>
			</template>

			<template #body="{ togglePopover }">
				<div class="w-80 z-50 shadow-xl border border-gray-200 rounded-lg bg-white">
					<div class="border-b border-gray-200 p-3 rounded-t-lg">
						<FormControl
							v-model="searchQuery"
							placeholder="Search icons..."
							class="w-full border border-gray-200"
						/>
					</div>

					<div class="max-h-[300px] overflow-y-auto p-3">
						<Button
							v-for="icon in filteredIcons"
							:key="icon"
							size="sm"
							variant="ghost"
							class="mx-0.5 my-0.5 h-12 w-12 p-0 justify-center hover:bg-gray-100"
							:class="model === icon ? 'bg-gray-100 ring-1 ring-gray-300' : ''"
							@click="
								selectIcon(icon)
								togglePopover(false)
							"
						>
							<component
								v-if="iconMap[icon as keyof typeof iconMap]"
								:is="iconMap[icon as keyof typeof iconMap]"
								class="h-5 w-5 fill-current stroke-0"
							/>
							<span v-else class="text-lg leading-none">{{ icon }}</span>
						</Button>
					</div>

					<div class="flex items-center p-3 border-t border-gray-200 rounded-b-lg">
						<Button
							variant="outline"
							class="gap-2"
							size="sm"
							@click="
								clearIcon()
								togglePopover(false)
							"
						>
							<X class="h-4 w-4" />
							Clear
						</Button>
					</div>
				</div>
			</template>
		</Popover>
	</div>
</template>
