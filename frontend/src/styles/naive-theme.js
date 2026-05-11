import { computed } from 'vue'
import { currentSkin } from './skins'

export const themeOverrides = computed(() => {
  const isV5 = currentSkin.value === 'v5'

  if (isV5) {
    return {
      common: {
        primaryColor: '#3f8b5b',
        primaryColorHover: '#35794c',
        primaryColorPressed: '#2f6d48',
        primaryColorSuppl: '#3f8b5b',
        borderRadius: '14px',
        borderRadiusSmall: '12px',
        fontSize: '15px',
        fontSizeMedium: '15px',
        textColorBase: '#262621',
        textColor1: '#262621',
        textColor2: '#4a4740',
        textColor3: '#5e5a51',
        dividerColor: '#e8e1d6',
        borderColor: '#e8e1d6',
        inputColor: '#ffffff',
        actionColor: '#f5f2ec',
        tableColor: '#ffffff',
        hoverColor: '#f5f3ee',
        fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif'
      },
      Layout: {
        siderColor: '#fffdfa',
        siderBorderColor: '#e8e1d6',
        siderToggleColor: '#e8e1d6',
        color: '#f5f2ec',
        headerColor: '#fffdfa'
      },
      Menu: {
        borderRadius: '16px',
        itemTextColor: '#5e5a51',
        itemTextColorHover: '#262621',
        itemTextColorActive: '#2f6d48',
        itemTextColorChildActive: '#2f6d48',
        itemColorActive: 'linear-gradient(180deg, #edf5ef 0%, #e8f2eb 100%)',
        itemColorHover: '#f5f3ee',
        itemColorActiveHover: '#e8f2eb',
        itemIconColor: '#7e7a71',
        itemIconColorHover: '#262621',
        itemIconColorActive: '#2f6d48',
        itemIconColorChildActive: '#2f6d48',
        arrowColor: '#a39d92',
        fontSize: '15px',
        fontSizeHorizontal: '15px',
        itemHeight: '46px',
        borderColorHorizontal: '#e8e1d6',
        groupTextColor: '#a39d92'
      },
      Button: {
        borderRadiusMedium: '14px',
        borderRadiusSmall: '12px',
        fontSizeMedium: '15px',
        fontSizeSmall: '14px',
        heightMedium: '40px'
      }
    }
  }

  return {
    common: {
      primaryColor: '#7f9b7a',
      primaryColorHover: '#6e8d69',
      primaryColorPressed: '#5e7d59',
      primaryColorSuppl: '#7f9b7a',
      borderRadius: '14px',
      borderRadiusSmall: '12px',
      fontSize: '15px',
      fontSizeMedium: '15px',
      textColorBase: '#2f3a32',
      textColor1: '#2f3a32',
      textColor2: '#465048',
      textColor3: '#5b635e',
      dividerColor: '#ddd7cc',
      borderColor: '#ddd7cc',
      inputColor: '#ffffff',
      actionColor: '#f7f4ee',
      tableColor: '#ffffff',
      hoverColor: '#f3f0e8',
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif'
    },
    Layout: {
      siderColor: '#fbfaf7',
      siderBorderColor: '#ddd7cc',
      siderToggleColor: '#ddd7cc',
      color: '#f5f3ee',
      headerColor: '#fbfaf7'
    },
    Menu: {
      borderRadius: '16px',
      itemTextColor: '#465048',
      itemTextColorHover: '#2f3a32',
      itemTextColorActive: '#30422f',
      itemTextColorChildActive: '#30422f',
      itemColorActive: '#e6efe3',
      itemColorHover: '#f3f0e8',
      itemColorActiveHover: '#e6efe3',
      itemIconColor: '#5b635e',
      itemIconColorHover: '#2f3a32',
      itemIconColorActive: '#30422f',
      itemIconColorChildActive: '#30422f',
      arrowColor: '#889286',
      fontSize: '15px',
      fontSizeHorizontal: '15px',
      itemHeight: '46px',
      borderColorHorizontal: '#ddd7cc',
      groupTextColor: '#6e746f'
    },
    Button: {
      borderRadiusMedium: '14px',
      borderRadiusSmall: '12px',
      fontSizeMedium: '15px',
      fontSizeSmall: '14px',
      heightMedium: '40px'
    }
  }
})
