<script setup>
import widgets from '@/widgets/widgets'
import { Download, Database } from 'lucide-vue-next'
import useMarketplaceStore from '@/stores/marketplaceStore'

const marketplaceStore = useMarketplaceStore()
const props = defineProps({
	template: { type: Object, required: true },
})

function handleImport() {
	marketplaceStore.openImportDialog(props.template)
}
</script>

<template>
	<div class="text-base">
		<div class="flex gap-4">
			<div class="relative flex h-60 w-1/3 items-center justify-center rounded bg-gray-50">
				<span class="text-sm text-gray-600"> Loading Preview... </span>
			</div>
			<div class="flex flex-1 flex-col p-2">
				<div class="flex items-center justify-between">
					<div class="text-xl font-bold">{{ template.title }}</div>
					<div class="text-sm text-gray-600">
						{{ template.modifiedFromNow }}
					</div>
				</div>
				<div class="mt-1 text-lg text-gray-700">
					{{ template.description }}
				</div>
				<div class="mt-2 flex items-center justify-between">
					<div class="mt-2 flex items-center gap-2">
						<Avatar :label="template.author_name" size="lg" />
						<span class="text-gray-700">
							{{ template.author_name }}
						</span>
					</div>
					<Button variant="solid" @click="handleImport">
						<template #prefix> <Download class="h-4 w-4" /></template>
						<span>Import</span>
					</Button>
				</div>
				<div class="mt-4">
					<p class="font-bold">Data</p>
					<!-- list of charts -->
					<ul class="mt-2 space-y-2">
						<li
							v-for="(data_source, idx) of template.data_sources"
							:key="idx"
							class="flex items-center gap-2"
						>
							<Database class="h-4 w-4 text-gray-600" />
							<span class="text-gray-700"> {{ data_source.type }} </span>
						</li>
					</ul>
				</div>
				<div class="mt-4">
					<p class="font-bold">Charts</p>
					<!-- list of charts -->
					<ul class="mt-2 space-y-2">
						<li
							v-for="(chart, idx) of template.charts"
							:key="idx"
							class="flex items-center gap-2"
						>
							<component
								v-if="widgets[chart.type]"
								:is="widgets[chart.type].icon"
								class="h-4 w-4 text-gray-600"
							/>
							<span class="text-gray-700"> {{ chart.title }} </span>
						</li>
					</ul>
				</div>
			</div>
		</div>
	</div>
</template>
