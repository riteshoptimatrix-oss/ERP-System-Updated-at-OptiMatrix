export interface ApiError {
  code: number;
  message: string;
  correlation_id?: string;
  details?: Array<{
    field: string;
    message: string;
    type: string;
  }>;
}

export interface ApiResponse<T> {
  data?: T;
  error?: ApiError;
  status: number;
}

export interface DependencyStatus {
  status: 'connected' | 'disconnected' | 'degraded';
  latency_ms: number;
  details: string;
}

export interface ReadinessData {
  status: 'ready' | 'not_ready';
  dependencies: {
    mongodb: DependencyStatus;
    [key: string]: DependencyStatus;
  };
}

export interface LivenessData {
  status: 'healthy' | 'unhealthy';
  environment: string;
  version: string;
}
