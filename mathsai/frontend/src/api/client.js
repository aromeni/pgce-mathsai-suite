import axios from "axios";

// Relative baseURL: in dev this is proxied to the backend by vite.config.js;
// in production both are served from the same origin. No other file should
// call axios/fetch directly — every request goes through this client.
const client = axios.create({
  baseURL: "/api",
});

// A 401 means the session cookie expired or was cleared server-side. The
// login page is server-rendered and lives outside this bundle (see
// backend/auth.py), so the only recovery is a full navigation rather than a
// React route change. Guarded against redirect loops if /login itself 401s.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && window.location.pathname !== "/login") {
      window.location.assign("/login");
    }
    return Promise.reject(error);
  },
);

export const logout = () =>
  client.post("/auth/logout").then(() => window.location.assign("/login"));

export const getTopics = () => client.get("/topics").then((res) => res.data);

export const getTopicsByKeyStage = (keyStage) =>
  client.get(`/topics/${keyStage.toLowerCase()}`).then((res) => res.data);

export const searchTopics = (query) =>
  client.get("/topics/search", { params: { q: query } }).then((res) => res.data);

export const getTopic = (topicId) =>
  client.get(`/topics/${topicId}`).then((res) => res.data);

export const getLesson = (topicId) =>
  client.get(`/lessons/${topicId}`).then((res) => res.data);

export const refreshLesson = (topicId) =>
  client.post(`/lessons/${topicId}/refresh`).then((res) => res.data);

export const getQuestions = (topicId, difficulty) =>
  client.get(`/questions/${topicId}/${difficulty}`).then((res) => res.data);

export const refreshQuestions = (topicId, difficulty) =>
  client.post(`/questions/${topicId}/${difficulty}/refresh`).then((res) => res.data);

export const getQuestionsStatus = (topicId, difficulty) =>
  client.get(`/questions/${topicId}/${difficulty}/status`).then((res) => res.data);

export const markQuestionsReviewed = (topicId, difficulty) =>
  client.post(`/questions/${topicId}/${difficulty}/review`).then((res) => res.data);

export const markLessonReviewed = (topicId) =>
  client.post(`/lessons/${topicId}/review`).then((res) => res.data);

export const getProgress = () => client.get("/progress").then((res) => res.data);

export const getTopicProgress = (topicId) =>
  client.get(`/progress/topic/${topicId}`).then((res) => res.data);

export const logTaught = (entry) =>
  client.post("/progress", entry).then((res) => res.data);

export const deleteProgress = (logId) =>
  client.delete(`/progress/${logId}`).then((res) => res.data);

function extractFilename(contentDisposition, fallback) {
  const match = contentDisposition?.match(/filename="?([^"]+)"?/);
  return match ? match[1] : fallback;
}

function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export const exportLessonPdf = (topicId) =>
  client.get(`/export/lesson/${topicId}/pdf`, { responseType: "blob" }).then((res) => {
    downloadBlob(res.data, extractFilename(res.headers["content-disposition"], `lesson-${topicId}.pdf`));
  });

export const exportQuestionsPdf = (topicId) =>
  client.get(`/export/questions/${topicId}/pdf`, { responseType: "blob" }).then((res) => {
    downloadBlob(res.data, extractFilename(res.headers["content-disposition"], `questions-${topicId}.pdf`));
  });

export default client;
