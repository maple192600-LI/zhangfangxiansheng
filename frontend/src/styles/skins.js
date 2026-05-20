import { ref, watch } from 'vue'

export const SKINS = {
  classic: {
    label: '墨绿',
    cssVars: {
      '--bg': '#f5f3ee',
      '--bg-gradient': 'linear-gradient(180deg, #f6f4ef 0%, #f1eee7 100%)',
      '--panel': '#fbfaf7',
      '--panel-2': '#ffffff',
      '--line': '#ddd7cc',
      '--line-soft': '#ebe6dc',
      '--line-table': '#eee7da',
      '--line-table-vert': '#f0eadf',
      '--text': '#2f3a32',
      '--text-secondary': '#465048',
      '--text-tertiary': '#5b635e',
      '--text-light': '#6a706c',
      '--muted': '#6e746f',
      '--green': '#7f9b7a',
      '--green-hover': '#6e8d69',
      '--green-2': '#e6efe3',
      '--green-3': '#f0f6ee',
      '--accent': '#c8b48a',
      '--warn': '#b87b5d',
      '--warn-bg': '#faeee8',
      '--warn-border': '#ebd0c2',
      '--warn-text': '#7f4b32',
      '--info': '#6e88a7',
      '--info-bg': '#eef3f8',
      '--info-border': '#d8e1ec',
      '--info-text': '#4f6681',
      '--ok-bg': '#edf4ea',
      '--ok-border': '#d9e6d4',
      '--ok-text': '#3f5b3d',
      '--tag-green-bg': '#e7f0e4',
      '--tag-green-text': '#2f5a2f',
      '--tag-green-border': '#cfe1cc',
      '--tag-warn-bg': '#f7e9e1',
      '--tag-warn-text': '#874f32',
      '--tag-warn-border': '#ebd0c2',
      '--tag-gray-bg': '#f2f1ed',
      '--tag-gray-text': '#676d68',
      '--tag-gray-border': '#e5e2da',
      '--tag-blue-bg': '#e8eef5',
      '--tag-blue-text': '#3e5a7a',
      '--tag-blue-border': '#c9d5e3',
      '--thead-bg': '#f7f4ee',
      '--radius-lg': '22px',
      '--radius': '18px',
      '--radius-md': '16px',
      '--radius-sm': '12px',
      '--radius-pill': '999px',
      '--shadow': '0 8px 24px rgba(60, 60, 40, 0.08)',
      '--shadow-card-subtle': '0 2px 8px rgba(60, 60, 40, 0.04)',
      '--space-xs': '6px',
      '--space-sm': '10px',
      '--space-md': '14px',
      '--space-lg': '16px',
      '--space-xl': '18px',
      '--space-2xl': '20px',
      '--space-3xl': '22px',
      '--space-section': '32px',
      '--font-size-xs': '13px',
      '--font-size-sm': '14px',
      '--font-size-base': '15px',
      '--font-size-md': '16px',
      '--font-size-lg': '18px',
      '--font-size-xl': '22px',
      '--font-size-hero': '30px',
      '--font-family': '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
      '--sidebar-width': '290px'
    }
  },
  fresh: {
    label: '新竹',
    cssVars: {
      '--bg': '#f5f2ec',
      '--bg-gradient': 'radial-gradient(circle at top left, rgba(97,154,117,.09), transparent 26%), radial-gradient(circle at top right, rgba(192,159,115,.09), transparent 22%), linear-gradient(180deg, #f7f5ef 0%, #f4f1ea 100%)',
      '--panel': '#fffdfa',
      '--panel-2': '#ffffff',
      '--line': '#e8e1d6',
      '--line-soft': '#f0ebe0',
      '--line-table': '#eee7da',
      '--line-table-vert': '#f0eadf',
      '--text': '#262621',
      '--text-secondary': '#4a4740',
      '--text-tertiary': '#5e5a51',
      '--text-light': '#7e7a71',
      '--muted': '#7e7a71',
      '--green': '#3f8b5b',
      '--green-hover': '#35794c',
      '--green-2': '#e7f0ea',
      '--green-3': '#f0f6f1',
      '--accent': '#b9854d',
      '--warn': '#b87b5d',
      '--warn-bg': '#faeee8',
      '--warn-border': '#ebd0c2',
      '--warn-text': '#7f4b32',
      '--info': '#6e88a7',
      '--info-bg': '#eef3f8',
      '--info-border': '#d8e1ec',
      '--info-text': '#4f6681',
      '--ok-bg': '#edf5ef',
      '--ok-border': '#d4e8d8',
      '--ok-text': '#2f5b3d',
      '--tag-green-bg': '#eaf2ed',
      '--tag-green-text': '#2f6d48',
      '--tag-green-border': '#d4e8da',
      '--tag-warn-bg': '#f7e9e1',
      '--tag-warn-text': '#874f32',
      '--tag-warn-border': '#ebd0c2',
      '--tag-gray-bg': '#f3f1ec',
      '--tag-gray-text': '#67625a',
      '--tag-gray-border': '#e5e1d8',
      '--tag-blue-bg': '#e8eef5',
      '--tag-blue-text': '#3e5a7a',
      '--tag-blue-border': '#c9d5e3',
      '--thead-bg': '#f5f2ec',
      '--radius-lg': '22px',
      '--radius': '18px',
      '--radius-md': '16px',
      '--radius-sm': '12px',
      '--radius-pill': '999px',
      '--shadow': '0 18px 45px rgba(70, 52, 26, 0.08)',
      '--shadow-card-subtle': '0 10px 24px rgba(70, 52, 26, 0.06)',
      '--space-xs': '6px',
      '--space-sm': '10px',
      '--space-md': '14px',
      '--space-lg': '16px',
      '--space-xl': '18px',
      '--space-2xl': '20px',
      '--space-3xl': '22px',
      '--space-section': '32px',
      '--font-size-xs': '13px',
      '--font-size-sm': '14px',
      '--font-size-base': '15px',
      '--font-size-md': '16px',
      '--font-size-lg': '18px',
      '--font-size-xl': '22px',
      '--font-size-hero': '30px',
      '--font-family': '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
      '--sidebar-width': '290px'
    }
  }
}

export const currentSkin = ref(localStorage.getItem('zf_skin') || 'classic')

export function useSkin() {
  function setSkin(name) {
    if (SKINS[name]) {
      currentSkin.value = name
    }
  }

  function getSkinName() {
    return currentSkin.value
  }

  function getSkinLabel() {
    return SKINS[currentSkin.value]?.label || '墨绿'
  }

  watch(currentSkin, (name) => {
    localStorage.setItem('zf_skin', name)
    const vars = SKINS[name]?.cssVars
    if (vars) {
      const root = document.documentElement
      for (const [k, v] of Object.entries(vars)) {
        root.style.setProperty(k, v)
      }
    }
  }, { immediate: true })

  return { currentSkin, setSkin, getSkinName, getSkinLabel, skins: SKINS }
}
