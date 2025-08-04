import { defineStore } from 'pinia'
import { ref } from 'vue'
import { FormattingMode,FormatGroupArgs } from '../query/components/formatting_utils'

//basic store to manage formatting of columns
export const useFormatStore = defineStore('formatStore', () => {
  
  const conditionalFormatting = ref<FormatGroupArgs>({
    formats: [],
    columns: [],
  })

  function setFormatting(formatGroup: FormatGroupArgs) {
    conditionalFormatting.value = formatGroup
  }

  function clearFormatting() {
    conditionalFormatting.value = {
      formats: [],
      columns: [],
    }
  }

  function addFormat(format: FormattingMode) {
    conditionalFormatting.value.formats.push(format)
  }

  function removeFormat(index: number) {
    conditionalFormatting.value.formats.splice(index, 1)
  }

  function updateFormat(index: number, format: FormattingMode) {
    conditionalFormatting.value.formats[index] = format
  }

  return {
    conditionalFormatting,
    setFormatting,
    clearFormatting,
    addFormat,
    removeFormat,
    updateFormat,
  }
})
