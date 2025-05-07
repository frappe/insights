<script setup lang="ts">
import { debounce } from "frappe-ui";
import { computed, onMounted, ref } from "vue";
import { flattenOptions } from "../../helpers";
import { ColumnOption, GroupedColumnOption } from "../../types/query.types";
import { column, value, filter } from "../helpers";
import useQuery from "../query";
import {
  FormattingMode,
  ConditionalOperator,
  ColorByPercentage,
} from "./formatting_utils";

const format = defineModel<FormattingMode>({ required: true });
const props = defineProps<{
  columnOptions: ColumnOption[] | GroupedColumnOption[];
}>();

onMounted(() => {
  if (valueSelectorType.value === "select") fetchColumnValues();
});

function onColumnChange(column_name: string) {
  if (format.value.mode === "cell_rules") {
    format.value.column = column(column_name);
    format.value.operator = operatorOptions[0].value;
    if (valueSelectorType.value === "select") {
      format.value.value = [];
      fetchColumnValues();
    }
  } else {
    format.value.column = column(column_name);
    format.value.colorScale;
    if (valueSelectorType.value === "select") {
      format.value.value = [];
      fetchColumnValues();
    }
  }
}

const valueSelectorType = computed(() => {
  if (!format.value.column.column_name || !columnType.value) {
    return;
  } else if (format.value.mode === "cell_rules") {
    return "number";
  } else {
    return "select";
  }
});

const columnType = computed(() => {
  if (!props.columnOptions?.length) return;
  if (!format.value.column.column_name) return;
  const options = flattenOptions(props.columnOptions) as ColumnOption[];
  const col = options.find((c) => c.value === format.value.column.column_name);
  if (!col)
    throw new Error(`Column not found: ${format.value.column.column_name}`);
  return col.data_type;
});

const formatModeOptions = [
  { label: "Highlight Cells", value: "cell_rules" },
  { label: "Color Scales", value: "color_scale" },
];

const highlightColorOptions = [
  { label: "Red", value: "red" },
  { label: "Green", value: "green" },
  { label: "Amber", value: "amber" },
];

function onOperatorChange(operator: ConditionalOperator) {
  if (format.value.mode === "cell_rules") {
    format.value.operator = operator;
  } else null;
}

function onColorScaleChange(newColor: string) {
  if (format.value.mode === "color_scale") {
    format.value.colorScale = newColor;
  }
}

function onHighlightColorChange(newColor: string) {
  if (format.value.mode === "cell_rules") {
    format.value.color = newColor;
  } else null;
}

function onFormatModeChange(newMode: FormattingMode["mode"]) {
  format.value.mode = newMode;
}

const operatorOptions: { label: string; value: ConditionalOperator }[] = [
  { label: "equals", value: "=" },
  { label: "not equals", value: "!=" },
  { label: "greater than", value: ">" },
  { label: "greater than or equals", value: ">=" },
  { label: "less than", value: "<" },
  { label: "less than or equals", value: "<=" },
];
const colorScaleOptions = [
  {
    label: "Red-Amber-Green",
    value: "RAG",
  },
  {
    label: "Green-Amber-Red",
    value: "GAR",
  },
];

const distinctColumnValues = ref<any[]>([]);
const fetchingValues = ref(false);
const fetchColumnValues = debounce((searchTxt: string) => {
  const options = flattenOptions(props.columnOptions) as ColumnOption[];
  const option = options.find(
    (c) => c.value === format.value!.column.column_name,
  );
  if (!option?.query) {
    fetchingValues.value = false;
    console.warn(
      "Query not found for column:",
      format.value!.column.column_name,
    );
    return;
  }
  // only for dashboard filters
  // if column_name is {sep}query{sep}.{sep}column_name{sep} extract column_name
  const sep = "`";
  const pattern = new RegExp(
    `${sep}([^${sep}]+)${sep}\\.${sep}([^${sep}]+)${sep}`,
  );
  const match = pattern.exec(format.value.column.column_name);
  const column_name = match ? match[2] : format.value.column.column_name;

  fetchingValues.value = true;
  return useQuery(option.query)
    .getDistinctColumnValues(column_name, searchTxt)
    .then((values: string[]) => (distinctColumnValues.value = values))
    .finally(() => (fetchingValues.value = false));
}, 300);
</script>

<template>
	<div class="flex flex-1 gap-2 flex-nowrap"> 
		 <div id="column_name" class="flex-1 min-w-0">
			 <Autocomplete
					placeholder="Column"
					:modelValue="format.column!.column_name"
					:options="props.columnOptions"
					@update:modelValue="onColumnChange($event?.value)"
					class="w-full" />
</div>

<div class="flex-1 min-w-0">
	 <FormControl
			type="select"
			placeholder="Formatting Mode"
			:disabled="!columnType"
			:modelValue="format.mode"
			:options="formatModeOptions"
			@update:modelValue="onFormatModeChange($event)"
			class="w-full"
	/>
</div>

<div id="operator" class="flex-1 min-w-0"> 
	<FormControl
		type="select"
		v-show="format.mode === 'cell_rules'"
		v-if="format.mode === 'cell_rules'"
		placeholder="Operator"
		:disabled="!columnType"
		:modelValue="format.operator"
		:options="operatorOptions"
		@update:modelValue="onOperatorChange($event)"
		class="w-full"
	/>
	<FormControl
		type="select"
		v-show="format.mode === 'color_scale'"
		v-if="format.mode === 'color_scale'"
		placeholder="Color Scale"
		:disabled="!columnType"
		:modelValue="format.colorScale"
		:options="colorScaleOptions"
		@update:modelValue="onColorScaleChange($event)"
		class="w-full"
	/>
</div>

<div id="value" class="flex-1 min-w-0 flex items-start gap-2">
	<div v-if="format.mode === 'cell_rules' && valueSelectorType === 'number'" class="flex-1 min-w-0">
		<FormControl
			type="number"
			:modelValue="format.value"
			placeholder="Value"
			@update:modelValue="format.value = Number($event)"
			class="w-full"
		/>
	</div>

	<div v-if="format.mode === 'cell_rules'" class="flex-1 min-w-0">
		 <FormControl
			type="select"
			placeholder="Color"
			:disabled="!columnType"
			:modelValue="format.color"
			:options="highlightColorOptions"
			@update:modelValue="onHighlightColorChange($event)"
			class="w-full"
		/>
	</div>
</div>
</div>
</template>
