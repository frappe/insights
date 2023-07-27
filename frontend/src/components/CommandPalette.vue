<template>
	<transition name="fade">
		<div
			v-show="show"
			class="absolute z-10 flex h-full w-full justify-center bg-gray-50/60 pt-20 text-base backdrop-blur-sm backdrop-grayscale"
		>
			<div class="max-h-[28rem] w-[38rem] rounded border bg-white shadow-md">
				<div class="flex items-center border-b px-3">
					<FeatherIcon name="search" class="absolute h-4 w-4 text-gray-600" />
					<input
						ref="searchInput"
						v-model="searchTerm"
						class="ml-2 flex h-12 w-full items-center rounded-t-md px-4 focus:outline-none"
						placeholder="Search..."
					/>
				</div>
				<div class="mt-2 flex flex-col px-2">
					<div v-if="commands.length > 0">
						<div class="text-sm text-gray-600">Navigation</div>
						<div
							v-for="(command, idx) in commands"
							class="-mx-2 flex h-10 cursor-pointer items-center space-x-2 px-2"
							@mouseenter="activeIndex = idx"
							:class="[activeIndex === idx ? 'bg-gray-50' : '']"
							@click="
								() => {
									commandPalette.close()
									command.action()
								}
							"
						>
							<FeatherIcon
								:name="command.icon || 'arrow-right'"
								class="h-4 w-4 text-gray-600"
							/>
							<div class="flex items-baseline">
								<span>{{ command.title }}</span>
								<span class="ml-2 text-sm text-gray-600">
									{{ command.description }}
								</span>
							</div>
						</div>
					</div>
					<div v-else class="text-sm text-gray-600">No results found</div>
				</div>
			</div>
		</div>
	</transition>
</template>

<script setup>
import { ref, watch, computed, nextTick } from 'vue'
import { useMagicKeys } from '@vueuse/core'
import useCommandPalette from '@/utils/commandPalette'

const commandPalette = useCommandPalette()

const keys = useMagicKeys()
const cmdK = keys['Meta+K']
const escape = keys['Escape']
const searchInput = ref()

const show = computed(() => commandPalette.isOpen)
watch(cmdK, (pressed) => {
	if (pressed) {
		commandPalette.open()
	}
})
watch(escape, (pressed) => {
	if (pressed && show.value) {
		commandPalette.close()
	}
})

watch(show, (value) => {
	if (value) {
		nextTick(() => {
			searchInput.value.focus()
		})
	}
})

const searchTerm = ref('')
const commands = computed(() => {
	return commandPalette.search(searchTerm.value)
})

const activeIndex = ref(0)
const ArrowDown = keys['ArrowDown']
const ArrowUp = keys['ArrowUp']

watch(ArrowDown, (pressed) => {
	if (pressed && show.value) {
		activeIndex.value = Math.min(commands.value.length - 1, activeIndex.value + 1)
	}
})
watch(ArrowUp, (pressed) => {
	if (pressed && show.value) {
		activeIndex.value = Math.max(0, activeIndex.value - 1)
	}
})

const enter = keys['Enter']
watch(enter, (pressed) => {
	if (pressed && show.value) {
		commandPalette.close()
		commands.value[activeIndex.value].action()
	}
})
</script>

<style>
.fade-enter-active,
.fade-leave-active {
	transition: opacity 0.2s ease-out;
}

.fade-enter-from,
.fade-leave-to {
	opacity: 0;
}
</style>
