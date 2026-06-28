type DebugFn = ((...args: unknown[]) => void) & {
  enabled: boolean
  extend: (namespace: string) => DebugFn
}

function createDebug(): DebugFn {
  const debug = (() => undefined) as DebugFn
  debug.enabled = false
  debug.extend = () => createDebug()
  return debug
}

const debugFactory = Object.assign(
  (namespace: string) => {
    void namespace
    return createDebug()
  },
  {
    coerce: (value: unknown) => value,
    disable: () => '',
    enable: (_namespaces: string) => undefined,
    enabled: (_namespace: string) => false,
    formatArgs: (_args: unknown[]) => undefined,
    humanize: (value: unknown) => String(value),
    log: (..._args: unknown[]) => undefined,
  },
)

export default debugFactory
