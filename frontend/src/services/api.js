
import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const csrfToken = document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrf_access_token="))
    ?.split("=")[1];

  if (csrfToken) {
    config.headers["X-CSRF-TOKEN"] = csrfToken;
  }

  // Let Axios/browser set multipart Content-Type and boundary.
  if (config.data instanceof FormData) {
    delete config.headers["Content-Type"];
  }

  return config;
});

// ============================================================
// CLIENT-SIDE IN-MEMORY CACHE & REQUEST DEDUPLICATION
// ============================================================

const cache = new Map();
const inFlight = new Map();

// Route TTL rules in milliseconds
const CACHE_RULES = [
  { pattern: /\/admin\/departments/i, ttl: 60000 },
  { pattern: /\/admin\/batches/i, ttl: 60000 },
  { pattern: /\/admin\/students\/filter-options/i, ttl: 60000 },
  { pattern: /\/admin\/faculty\/filter-options/i, ttl: 60000 },
  { pattern: /\/admin\/students\/summary/i, ttl: 20000 },
  { pattern: /\/admin\/faculty\/summary/i, ttl: 20000 },
  { pattern: /\/admin\/academic\/summary/i, ttl: 20000 },
  { pattern: /\/admin\/courses/i, ttl: 30000 },
  { pattern: /\/admin\/course-offerings/i, ttl: 20000 },
  { pattern: /\/admin\/students/i, ttl: 15000 },
  { pattern: /\/admin\/faculty/i, ttl: 20000 },
  { pattern: /\/admin\/users/i, ttl: 20000 },
  { pattern: /\/faculty\/classes\/summary/i, ttl: 20000 },
  { pattern: /\/faculty\/courses/i, ttl: 20000 },
  { pattern: /\/faculty\/students/i, ttl: 20000 },
  { pattern: /\/student\/courses/i, ttl: 30000 },
  { pattern: /\/timetable\/admin/i, ttl: 20000 },
  { pattern: /\/timetable\/faculty/i, ttl: 20000 },
  { pattern: /\/timetable\/student/i, ttl: 20000 },
  { pattern: /\/timetable\/adjustments/i, ttl: 15000 },
];

function getTtlForUrl(url) {
  for (const rule of CACHE_RULES) {
    if (rule.pattern.test(url)) {
      return rule.ttl;
    }
  }
  return 0; // Not cached long-term (only in-flight deduplicated)
}

function getCacheKey(url, config = {}) {
  const params = config.params ? JSON.stringify(config.params) : "";
  return `GET:${url}:${params}`;
}

export function clearApiCache() {
  cache.clear();
  inFlight.clear();
}

export function invalidateApiCache(pattern) {
  const regex = pattern instanceof RegExp ? pattern : new RegExp(pattern, "i");
  for (const key of cache.keys()) {
    if (regex.test(key)) {
      cache.delete(key);
    }
  }
}

function autoInvalidateOnMutation(url) {
  const lowerUrl = String(url).toLowerCase();
  if (lowerUrl.includes("student")) {
    invalidateApiCache("student");
  }
  if (lowerUrl.includes("faculty")) {
    invalidateApiCache("faculty");
  }
  if (lowerUrl.includes("department")) {
    invalidateApiCache("department");
    invalidateApiCache("student");
    invalidateApiCache("faculty");
  }
  if (lowerUrl.includes("batch")) {
    invalidateApiCache("batch");
    invalidateApiCache("student");
  }
  if (lowerUrl.includes("course") || lowerUrl.includes("offering") || lowerUrl.includes("enrollment") || lowerUrl.includes("academic")) {
    invalidateApiCache("course");
    invalidateApiCache("offering");
    invalidateApiCache("enrollment");
    invalidateApiCache("academic");
    invalidateApiCache("timetable");
  }
  if (lowerUrl.includes("timetable") || lowerUrl.includes("adjustment")) {
    invalidateApiCache("timetable");
  }
  if (lowerUrl.includes("attendance")) {
    invalidateApiCache("attendance");
  }
  if (lowerUrl.includes("user")) {
    invalidateApiCache("user");
  }
}

// Wrap api.get for transparent in-flight deduplication and TTL caching
const rawGet = api.get.bind(api);
api.get = function cachedGet(url, config = {}) {
  // Respect Cache-Control: no-cache or explicit bypass
  if (config.headers?.["Cache-Control"] === "no-cache" || config.params?._nocache) {
    return rawGet(url, config);
  }

  const key = getCacheKey(url, config);
  const now = Date.now();

  // 1. Check valid cache entry
  const cached = cache.get(key);
  if (cached && cached.expiresAt > now) {
    return Promise.resolve({
      ...cached.response,
      data: JSON.parse(JSON.stringify(cached.response.data)), // Return fresh clone
      fromCache: true,
    });
  }

  // 2. Check active in-flight request
  if (inFlight.has(key)) {
    return inFlight.get(key).then((res) => ({
      ...res,
      data: JSON.parse(JSON.stringify(res.data)),
      fromDeduplication: true,
    }));
  }

  // 3. Launch network request
  const ttl = getTtlForUrl(url);
  const promise = rawGet(url, config)
    .then((response) => {
      inFlight.delete(key);
      if (ttl > 0 && response?.status === 200) {
        cache.set(key, {
          response: {
            data: response.data,
            status: response.status,
            statusText: response.statusText,
            headers: response.headers,
          },
          expiresAt: Date.now() + ttl,
        });
      }
      return response;
    })
    .catch((error) => {
      inFlight.delete(key);
      throw error;
    });

  inFlight.set(key, promise);
  return promise;
};

// Wrap mutation methods to trigger automatic cache invalidation
const rawPost = api.post.bind(api);
api.post = function (url, data, config) {
  return rawPost(url, data, config).then((res) => {
    autoInvalidateOnMutation(url);
    return res;
  });
};

const rawPatch = api.patch.bind(api);
api.patch = function (url, data, config) {
  return rawPatch(url, data, config).then((res) => {
    autoInvalidateOnMutation(url);
    return res;
  });
};

const rawPut = api.put.bind(api);
api.put = function (url, data, config) {
  return rawPut(url, data, config).then((res) => {
    autoInvalidateOnMutation(url);
    return res;
  });
};

const rawDelete = api.delete.bind(api);
api.delete = function (url, config) {
  return rawDelete(url, config).then((res) => {
    autoInvalidateOnMutation(url);
    return res;
  });
};

export default api;
