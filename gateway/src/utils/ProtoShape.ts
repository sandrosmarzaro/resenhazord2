// Dotted paths of the fields a proto message actually carries, never their values:
// enough to tell which fields WhatsApp delivered without logging message content.
export default class ProtoShape {
  private static readonly MAX_DEPTH = 4;

  static paths(node: unknown, prefix = '', depth = 0): string[] {
    if (!ProtoShape.isBranch(node) || depth === ProtoShape.MAX_DEPTH) {
      return prefix ? [prefix] : [];
    }
    return Object.entries(node)
      .filter(([, value]) => value !== null && value !== undefined && value !== '')
      .flatMap(([key, value]) =>
        ProtoShape.paths(value, prefix ? `${prefix}.${key}` : key, depth + 1),
      );
  }

  private static isBranch(node: unknown): node is Record<string, unknown> {
    return typeof node === 'object' && node !== null && !ArrayBuffer.isView(node);
  }
}
