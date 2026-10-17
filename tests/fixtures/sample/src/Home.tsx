import { useTranslation } from 'react-i18next'

export default function Home() {
  const { t } = useTranslation()
  return (
    <View>
      <Text>{t('home.title')}</Text>
      <Text>{t('home.greeting')}</Text>
      <Button title={t('common.ok')} />
      <Text>{t('home.subtitle_that_does_not_exist')}</Text>
    </View>
  )
}
