export interface HelloResponse {
  message: string;
}

export interface ErrorBody {
  code: string;
  message: string;
  request_id: string;
  details: Record<string, unknown>[] | null;
}

export interface ErrorEnvelope {
  error: ErrorBody;
}
