import { describe, it, expect, beforeEach, vi } from 'vitest';
import MockAdapter from 'axios-mock-adapter';
import AxiosClient from '../../../src/infra/AxiosClient.js';
import { addBreadcrumb } from '@sentry/bun';

describe('AxiosClient retry', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    AxiosClient.reset();
    vi.clearAllMocks();
    mock = new MockAdapter(AxiosClient.getInstance(), { delayResponse: 0 });
  });

  it('does not retry on 4xx errors', async () => {
    mock.onGet('/test').reply(404);

    await expect(AxiosClient.get('/test')).rejects.toThrow();
    expect(addBreadcrumb).not.toHaveBeenCalled();
  });

  it('retries on 500 and eventually throws', async () => {
    mock.onGet('/test').reply(500);

    await expect(AxiosClient.get('/test')).rejects.toThrow();
    expect(addBreadcrumb).toHaveBeenCalledTimes(3);
  });

  it('retries on 502 and eventually throws', async () => {
    mock.onGet('/test').reply(502);

    await expect(AxiosClient.get('/test')).rejects.toThrow();
    expect(addBreadcrumb).toHaveBeenCalledTimes(3);
  });

  it('retries on 503 and eventually throws', async () => {
    mock.onGet('/test').reply(503);

    await expect(AxiosClient.get('/test')).rejects.toThrow();
    expect(addBreadcrumb).toHaveBeenCalledTimes(3);
  });

  it('succeeds on second attempt (1 retry)', async () => {
    mock.onGet('/test').replyOnce(500).onGet('/test').reply(200, { ok: true });

    const response = await AxiosClient.get('/test');
    expect(response.data).toEqual({ ok: true });
    expect(addBreadcrumb).toHaveBeenCalledTimes(1);
  });

  it('calls addBreadcrumb with retry details on each retry', async () => {
    mock.onGet('/resource').reply(503);

    await expect(AxiosClient.get('/resource')).rejects.toThrow();

    expect(addBreadcrumb).toHaveBeenCalledTimes(3);
    expect(addBreadcrumb).toHaveBeenCalledWith(
      expect.objectContaining({
        category: 'http.retry',
        level: 'warning',
        data: expect.objectContaining({ status: 503 }),
      }),
    );
  });

  it('retries on network error (ECONNRESET)', async () => {
    mock.onGet('/test').networkError();

    await expect(AxiosClient.get('/test')).rejects.toThrow();
    expect(addBreadcrumb).toHaveBeenCalledTimes(3);
  });

  it('does not retry on 400', async () => {
    mock.onGet('/test').reply(400);

    await expect(AxiosClient.get('/test')).rejects.toThrow();
    expect(addBreadcrumb).not.toHaveBeenCalled();
  });

  it('does not retry on 401', async () => {
    mock.onGet('/test').reply(401);

    await expect(AxiosClient.get('/test')).rejects.toThrow();
    expect(addBreadcrumb).not.toHaveBeenCalled();
  });

  it('does not retry on 403', async () => {
    mock.onGet('/test').reply(403);

    await expect(AxiosClient.get('/test')).rejects.toThrow();
    expect(addBreadcrumb).not.toHaveBeenCalled();
  });

  it('does not retry when retries is set to 0', async () => {
    mock.onGet('/test').reply(500);

    await expect(AxiosClient.get('/test', { retries: 0 })).rejects.toThrow();
    expect(addBreadcrumb).not.toHaveBeenCalled();
  });
});
