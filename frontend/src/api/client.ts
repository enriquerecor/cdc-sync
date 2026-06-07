import createClient from "openapi-fetch";

import type { paths } from "./generated/openapi";
import { getApiBaseUrl } from "./config";

export const apiClient = createClient<paths>({
  baseUrl: getApiBaseUrl(),
});
