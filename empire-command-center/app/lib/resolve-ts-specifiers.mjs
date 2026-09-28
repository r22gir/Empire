/** Node test hook: app modules import extensionless paths; strip-types needs a file URL. */
export async function resolve(specifier, context, nextResolve) {
  if (
    (specifier.startsWith('./') || specifier.startsWith('../'))
    && !/\.(?:tsx?|jsx?|mjs|cjs|json)$/i.test(specifier)
  ) {
    try {
      return await nextResolve(`${specifier}.ts`, context);
    } catch {
      return nextResolve(specifier, context);
    }
  }
  return nextResolve(specifier, context);
}
