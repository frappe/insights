<script setup lang="ts">

import { computed, reactive, ref, watch, onMounted } from "vue";
import { copy, flattenOptions } from "../../helpers";
import RadioGroupItem from "../../components/ui/RadioGroupItem.vue";
import RadioGroup from "../../components/ui/Radio.vue";
import {
  ColumnOption,
  GroupedColumnOption,
} from "../../types/query.types";
import { column } from "../helpers";
import { FormatGroupArgs, FormattingMode } from "./formatting_utils";
import FormatRule from "./FormatRule.vue";

const props = defineProps<{
  formatMode?: FormattingMode;
  formatGroup?: FormatGroupArgs;
  columnOptions: ColumnOption[] | GroupedColumnOption[];
}>();

const emit = defineEmits<{
  close: []
  select: [formatGroup: FormatGroupArgs]
}>();

const selectedFormatMode = ref<"cell_rules" | "color_scale">(
  props.formatGroup?.formats[0]?.mode === "color_scale" ? "color_scale" : "cell_rules"
);

const formatGroup = reactive<FormatGroupArgs>(
  props.formatGroup
    ? copy(props.formatGroup)
    : {
        columns: [],
        formats: [],
      }
);

// Initialize the first format only if no formatGroup was provided
onMounted(() => {
  if (!props.formatGroup && formatGroup.formats.length === 0) {
    // TODO: Check cache first and fill the formatGroup with the cached data
    formatGroup.formats.push({
      mode: "cell_rules",
      column: column(""), // Start with empty column to show placeholder
      operator: "=",
      color: "red",
      value: 0, 
    });
  }
});

watch(selectedFormatMode, (newMode) => {
  if (formatGroup.formats.length > 0) {
    const currentColumn = formatGroup.formats[0].column;
    if (newMode === "color_scale") {
      formatGroup.formats[0] = {
        mode: "color_scale",
        column: currentColumn,
        colorScale: "RAG",
        value: undefined,
      };
    } else {
      formatGroup.formats[0] = {
        mode: "cell_rules",
        column: currentColumn,
        operator: "=",
        color: "red", 
        value: 0,
      };
    }
  }
});
</script>

<template>
  <div class="min-w-[20rem] rounded-lg bg-white px-4 pb-6 pt-5 sm:px-6">
    <div class="flex items-center justify-between pb-4">
      <h3 class="text-2xl font-semibold leading-6 text-gray-900">
        Conditional Formatting
      </h3>
      <Button variant="ghost" @click="() => emit('close')" icon="x" size="md">
      </Button>
    </div>
    <h3 class="text-sm text-gray-600 pb-3">
      Formatting Type
    </h3>
    <RadioGroup name="formatting-type" v-model="selectedFormatMode">
      <RadioGroupItem value="cell_rules">
        Highlight Cell
      </RadioGroupItem>
      <RadioGroupItem value="color_scale">
        Color Scale
      </RadioGroupItem>
    </RadioGroup>
        <FormatRule
      v-if="formatGroup.formats.length > 0"
      :modelValue="formatGroup.formats[0]"
      :columnOptions="props.columnOptions"
      :formatMode="selectedFormatMode"
      @update:modelValue="formatGroup.formats[0] = $event"
    />
    <div class="mt-6 flex items-center justify-end gap-2">
      <Button
        label="Cancel"
        variant="outline"
        @click="() => emit('close')"
      />
      <Button
        label="Apply Formatting"
        variant="solid"
        :disabled="!formatGroup.formats[0]?.column?.column_name"
        @click="() => emit('select', formatGroup)"
      />
    </div>
  </div>
</template>
