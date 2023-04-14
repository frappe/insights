<script setup>
import { getLoginLink } from '@/subscription'
import { CheckCircle } from 'lucide-vue-next'
import { ref } from 'vue'
const features = [
	'Unlimited Data Sources',
	'Unlimited Dashboards',
	'Unlimited Alerts',
	'Priority Support',
]

const loginLink = ref()
getLoginLink().then((link) => (loginLink.value = link))
</script>

<template>
	<div class="mt-40 h-full w-full">
		<div class="flex flex-col items-center justify-center">
			<p class="text-2xl font-semibold text-blue-500">Your free trial has ended</p>
			<h1 class="mb-3 mt-1 text-[48px] font-bold tracking-tight text-gray-900">
				Hope you enjoyed it!
			</h1>
			<div class="mx-auto w-[28rem] text-center text-xl font-light">
				Hello again! We hope you enjoyed your free trial of our service. Unfortunately, your
				trial has ended. To keep using Insights, please choose a plan below.
			</div>

			<div class="mt-8 flex space-x-3">
				<div
					class="flex max-w-[20rem] flex-col justify-between rounded-xl bg-white p-4 shadow-lg ring-1 ring-gray-900/10 sm:p-7"
				>
					<div>
						<h3 class="text-xl font-semibold leading-7 text-blue-500">Starter</h3>
						<div class="mt-3 flex items-baseline gap-x-2">
							<span class="text-[48px] font-bold tracking-tight text-gray-900">
								$10
							</span>
							<span class="text-xl leading-7 text-gray-500"> / month </span>
						</div>
						<p class="mt-4 text-lg text-gray-500">
							The perfect plan if you're just getting started with our product.
						</p>
						<ul role="list" class="mt-6 space-y-2 leading-6 text-gray-500">
							<li
								v-for="feature in features"
								:key="feature"
								class="flex items-center gap-x-2"
							>
								<CheckCircle
									class="h-4 w-4 flex-none text-blue-500"
									aria-hidden="true"
								/>
								{{ feature }}
							</li>
						</ul>
					</div>
					<a
						:href="loginLink"
						class="mt-8 block rounded-md bg-slate-800 px-3.5 py-2 text-center text-sm font-semibold leading-6 text-white shadow-sm hover:bg-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-700"
					>
						Get started today
					</a>
				</div>
			</div>
		</div>
	</div>
</template>
