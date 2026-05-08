import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

marked.setOptions({
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true,
  gfm: true,
})

export function useMarkdown() {
  function renderMarkdown(text) {
    if (!text) return ''
    return marked.parse(text)
  }

  return { renderMarkdown }
}
