<script setup>
import { inject, reactive, ref } from 'vue'
import { call } from 'frappe-ui'

const emit = defineEmits(['next', 'prev'])
const questions = reactive([
	{
		question: 'What type of data/database system(s) are you planning to connect with Insights?',
		answerOptions: [
			'I plan to connect to ERPNext',
			'I plan to use a SQL database (e.g., MySQL, PostgreSQL).',
			'I plan to use spreadsheets (e.g., Excel, Google Sheets).',
			'I plan to use a mix of different databases.',
			"I'm not sure yet.",
		],
		multipleAnswers: true,
		selectedAnswerIndexes: [],
	},
	{
		question: 'What is your level of familiarity with SQL and data analytics?',
		answerOptions: [
			"I'm a complete beginner with no experience in SQL or data analytics.",
			"I have some familiarity with data analytics, but I'm new to SQL.",
			"I've used SQL before but am not an expert.",
			"I'm quite comfortable with SQL and have done some data analysis.",
			"I'm an expert in SQL and have significant experience in data analytics.",
		],
		multipleAnswers: false,
		selectedAnswerIndexes: [],
	},
	{
		question: 'Which of the following best describes your role or use-case for Insights?',
		answerOptions: [
			"I'm a business owner/manager looking to monitor and understand key metrics.",
			"I'm a data analyst/scientist performing in-depth data exploration.",
			"I'm part of a team that needs to share data and reports with stakeholders.",
			"I'm in a tech role, exploring tools for our organization's data visualization needs.",
			"I'm just exploring and learning about data visualization and business intelligence tools.",
		],
		multipleAnswers: false,
		selectedAnswerIndexes: [],
	},
])

function toggleAnswer(question, index) {
	if (question.multipleAnswers) {
		if (question.selectedAnswerIndexes.includes(index)) {
			question.selectedAnswerIndexes = question.selectedAnswerIndexes.filter(
				(selectedIndex) => selectedIndex !== index
			)
		} else {
			question.selectedAnswerIndexes.push(index)
		}
	} else {
		question.selectedAnswerIndexes = [index]
	}
}

const $notify = inject('$notify')
const sendingResponses = ref(false)
async function validateAndContinue() {
	if (questions.some((question) => question.selectedAnswerIndexes.length === 0)) {
		$notify({
			title: 'Please answer all questions',
			message: 'You must select at least one answer for each question.',
			variant: 'error',
		})
	} else {
		sendingResponses.value = true
		const surveyResponses = questions.reduce((responses, question) => {
			responses[question.question] = question.selectedAnswerIndexes.map(
				(index) => question.answerOptions[index]
			)
			return responses
		}, {})
		await call('insights.api.setup.submit_survey_responses', {
			responses: surveyResponses,
		})
		sendingResponses.value = false
		emit('next')
	}
}

function skipAndContinue() {
	emit('next')
}
</script>

<template>
	<div class="mt-6 space-y-4">
		<div v-for="question in questions" :key="question.question" class="space-y-3">
			<div class="font-bold text-gray-900">{{ question.question }}</div>
			<div>
				<div
					v-if="question.multipleAnswers"
					v-for="(answerOption, index) in question.answerOptions"
					class="flex items-center space-x-2"
				>
					<input
						type="checkbox"
						:id="`${question.question}-${index}`"
						:checked="question.selectedAnswerIndexes.includes(index)"
						@change="toggleAnswer(question, index)"
						class="h-4 w-4 rounded border-gray-300"
					/>
					<label class="text-gray-700" :for="`${question.question}-${index}`">
						{{ answerOption }}
					</label>
				</div>

				<Input
					v-else
					type="select"
					:value="question.selectedAnswerIndexes[0]"
					@change="(value) => toggleAnswer(question, value)"
					:options="
						question.answerOptions.map((option, index) => ({
							label: option,
							value: index,
						}))
					"
				/>
			</div>
		</div>

		<div class="mt-6 flex justify-end space-x-3">
			<Button variant="outline" @click="skipAndContinue"> Skip </Button>
			<Button
				variant="solid"
				@click="validateAndContinue"
				:loading="sendingResponses"
				:disabled="
					sendingResponses ||
					questions.some((question) => question.selectedAnswerIndexes.length === 0)
				"
			>
				Continue
			</Button>
		</div>
	</div>
</template>
