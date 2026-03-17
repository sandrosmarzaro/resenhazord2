import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import axiosRetry from 'axios-retry';
import { Sentry } from './Sentry.js';

export interface RequestConfig {
  params?: Record<string, string | number | boolean>;
  headers?: Record<string, string>;
  timeout?: number;
  responseType?: 'json' | 'arraybuffer' | 'blob' | 'text' | 'stream';
  retries?: number;
}

export default class AxiosClient {
  private static instance: AxiosInstance | null = null;
  private static readonly DEFAULT_TIMEOUT = 30000;

  static getInstance(): AxiosInstance {
    if (!this.instance) {
      this.instance = axios.create({
        timeout: this.DEFAULT_TIMEOUT,
      });
      axiosRetry(this.instance, {
        retries: 3,
        retryDelay: axiosRetry.exponentialDelay,
        retryCondition: (error) => {
          if (error.code === 'ECONNABORTED' || error.code === 'ERR_CANCELED') return false;
          return !error.response || error.response.status >= 500;
        },
        onRetry: (retryCount, error, requestConfig) => {
          Sentry.addBreadcrumb({
            category: 'http.retry',
            message: Sentry.logger.fmt`Retrying ${requestConfig.url} (attempt ${retryCount})`,
            level: 'warning',
            data: { url: requestConfig.url, status: error.response?.status },
          });
        },
      });
    }
    return this.instance;
  }

  static async get<T = unknown>(url: string, config?: RequestConfig): Promise<AxiosResponse<T>> {
    return this.getInstance().get<T>(url, this.buildConfig(config));
  }

  static async post<T = unknown>(
    url: string,
    data?: unknown,
    config?: RequestConfig,
  ): Promise<AxiosResponse<T>> {
    return this.getInstance().post<T>(url, data, this.buildConfig(config));
  }

  static async getBuffer(url: string, config?: RequestConfig): Promise<Buffer> {
    const response = await this.get<ArrayBuffer>(url, { ...config, responseType: 'arraybuffer' });
    return Buffer.from(response.data);
  }

  private static buildConfig(config?: RequestConfig): AxiosRequestConfig {
    if (!config) return {};
    const axiosConfig: AxiosRequestConfig = {
      params: config.params,
      headers: config.headers,
      timeout: config.timeout,
      responseType: config.responseType,
    };
    if (config.retries !== undefined) {
      axiosConfig['axios-retry'] = { retries: config.retries };
    }
    return axiosConfig;
  }

  static reset(): void {
    this.instance = null;
  }

  static isInitialized(): boolean {
    return this.instance !== null;
  }
}
