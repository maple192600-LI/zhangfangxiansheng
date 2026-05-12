import { ref } from 'vue'

export function useReportPrint() {
  const printAreaRef = ref(null)

  function handlePrint() {
    window.print()
  }

  return { printAreaRef, handlePrint }
}
