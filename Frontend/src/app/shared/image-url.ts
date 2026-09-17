export function resolveImageUrl(imageUrl: string | null | undefined, apiRoot: string): string {
  const value = imageUrl?.trim() || '';
  if (!value || /^(https?:|data:|blob:)/i.test(value)) {
    return value;
  }

  return `${apiRoot.replace(/\/+$/, '')}/${value.replace(/^\/+/, '')}`;
}
