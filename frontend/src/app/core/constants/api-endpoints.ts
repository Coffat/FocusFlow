export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/api/v1/auth/login',
    REGISTER: '/api/v1/auth/register',
    REFRESH: '/api/v1/auth/refresh',
    LOGOUT: '/api/v1/auth/logout',
    ME: '/api/v1/auth/me',
  },
  ROADMAPS: {
    BASE: '/api/v1/roadmaps',
    GENERATE_STREAM: '/api/v1/roadmaps/generate-stream',
    ACTIVE: '/api/v1/roadmaps/active',
    APPLY: (id: string) => `/api/v1/roadmaps/${id}/apply`,
    PAUSE: (id: string) => `/api/v1/roadmaps/${id}/pause`,
    RESUME: (id: string) => `/api/v1/roadmaps/${id}/resume`,
    OVERDUE_REVISE: (id: string) => `/api/v1/roadmaps/${id}/overdue-revise-stream`,
  },
  TASKS: {
    BASE: '/api/v1/tasks',
    BACKLOG: '/api/v1/tasks/backlog',
    SCHEDULE_WEEK: '/api/v1/tasks/schedule/week',
  },
  SESSIONS: {
    BASE: '/api/v1/sessions',
    START: '/api/v1/sessions/start',
    HEARTBEAT: (id: string) => `/api/v1/sessions/${id}/heartbeat`,
    FINALIZE: (id: string) => `/api/v1/sessions/${id}/finalize`,
  },
  CALENDAR: {
    FEED: (token: string) => `/api/v1/calendar/feed/${token}.ics`,
    GENERATE_TOKEN: '/api/v1/calendar/tokens',
    RESET_TOKEN: '/api/v1/calendar/tokens/reset',
  },
  ANALYTICS: {
    SUMMARY: '/api/v1/analytics/summary',
    WEEKLY: '/api/v1/analytics/weekly',
  },
  SETTINGS: {
    PROFILE: '/api/v1/users/profile',
    QUOTA: '/api/v1/users/quota',
  }
} as const;
