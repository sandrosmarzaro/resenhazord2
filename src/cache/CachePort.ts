export interface CachePort<V> {
  get(key: string): Promise<V | undefined>;
  set(key: string, value: V): Promise<void>;
}
