export function useReportPrint() {
  function handlePrint() {
    window.print()
  }

  return { handlePrint }
}
