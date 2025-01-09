<script setup lang="ts">
import { call } from 'frappe-ui'
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import SharedChart from '../charts/SharedChart.vue'
import { WorkbookDashboard } from '../types/workbook.types'
import VueGridLayout from './VueGridLayout.vue'
import { jwtDecode } from "jwt-decode";


const props = defineProps<{ dashboard_name: string }>()


const dashboard = ref<WorkbookDashboard>()
const route = useRoute()
const keyValuePairs: Record<string, string[]> = {}

const jwtToken = route.query.token as string
let isAuthenticated = false


if (jwtToken) {
    try {

        const decodedToken = jwtDecode(jwtToken)
        const currentTime = Math.floor(Date.now() / 1000)

        if (decodedToken.exp && decodedToken.exp > currentTime) {
            isAuthenticated = true


            Object.entries(decodedToken.params || {}).forEach(([key, value]) => {
                if (Array.isArray(value)) {
                    keyValuePairs[key] = value
                } else {
                    keyValuePairs[key] = [value]
                }
            })
        } else {
            console.error('JWT token has expired')
        }
    } catch (error) {
        console.error('Invalid JWT token', error)
    }
} else {
    console.error('JWT token is missing')
}



dashboard.value = await call('insights.api.dashboards.fetch_workbook_dashboard', {
    dashboard_name: props.dashboard_name,
})


</script>


<template>
    <div class="relative flex h-full w-full overflow-hidden">
        <div class="flex-1 overflow-y-auto p-4">
            <div v-if="dashboard && dashboard.secure_embed && isAuthenticated">
                <VueGridLayout v-if="dashboard && dashboard.items.length > 0" class="h-fit w-full" :cols="20"
                    :disabled="true" :modelValue="dashboard.items.map((item) => item.layout)">
                    <template #item="{ index }">
                        <div class="relative h-full w-full rounded p-2">
                            <SharedChart :chart_name="dashboard.items[index].chart" :query="keyValuePairs" />
                        </div>
                    </template>
                </VueGridLayout>
            </div>
            <div v-else class="flex-1 flex items-center justify-center">
                <p class="text-red-500">Access Denied: Either token is invalid/expired or Sharing is Disabled</p>
            </div>
        </div>
    </div>
</template>
