import loc from '../locales/en.json'

// Property-access style, mixed into the same project.
export function ErrorBanner({ code }: { code: string }) {
  // A key built at runtime cannot be seen by static analysis.
  const dynamic = t(`errors.${code}`)
  return <Text>{loc.errors.network} {dynamic} {loc.common.cancel}</Text>
}
