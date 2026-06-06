import { useAppStore } from '../store/appStore'
import { en } from './en'
import { zh } from './zh'

export function useI18n() {
  const language = useAppStore((s) => s.language)
  const t = language === 'zh' ? zh : en
  return { t, language }
}

export { en, zh }
