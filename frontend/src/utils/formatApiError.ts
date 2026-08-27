import { ApiError } from "../api/client";

export function formatApiError(error: ApiError): string {
  switch (error.status) {
    case 0:
      return error.detail;
    case 415:
      return `Unsupported file: ${error.detail}`;
    case 413:
      return `Upload rejected: ${error.detail}`;
    case 401:
      return error.detail;
    case 403:
      return `Not permitted: ${error.detail}`;
    case 503:
      return error.detail;
    default:
      return `Request failed (${error.status}): ${error.detail}`;
  }
}
