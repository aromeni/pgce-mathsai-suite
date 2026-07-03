import axios from "axios";

// Relative baseURL: in dev this is proxied to the backend by vite.config.js;
// in production both are served from the same origin. No other file should
// call axios/fetch directly — every request goes through this client.
const client = axios.create({
  baseURL: "/api",
});

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

export const getProgress = () => client.get("/progress").then((res) => res.data);

export const getTopicProgress = (topicId) =>
  client.get(`/progress/topic/${topicId}`).then((res) => res.data);

export const logTaught = (entry) =>
  client.post("/progress", entry).then((res) => res.data);

export const deleteProgress = (logId) =>
  client.delete(`/progress/${logId}`).then((res) => res.data);

export default client;
