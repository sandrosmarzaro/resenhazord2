export default class UnsupportedGroupStatusError extends Error {
  constructor(kinds: string[]) {
    super(`A group status takes text, image, video or audio, got: ${kinds.join(', ')}`);
    this.name = 'UnsupportedGroupStatusError';
  }
}
