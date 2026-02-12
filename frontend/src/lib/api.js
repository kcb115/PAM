import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const api = {
  // Users
  createUser: (data) => axios.post(`${API}/users`, data),
  getUser: (userId) => axios.get(`${API}/users/${userId}`),
  updateUser: (userId, data) => axios.put(`${API}/users/${userId}`, data),

  // Spotify
  spotifyLogin: (userId) => axios.get(`${API}/spotify/login`, { params: { user_id: userId } }),
  checkSession: (sessionId) => axios.get(`${API}/spotify/session/${sessionId}`),

  // Taste Profile
  buildTasteProfile: (sessionId, userId) =>
    axios.post(`${API}/taste-profile/build?session_id=${sessionId}&user_id=${userId}`),
  getTasteProfile: (userId) => axios.get(`${API}/taste-profile/${userId}`),

  // Concert Discovery
  discoverConcerts: (data) => axios.post(`${API}/concerts/discover`, data),

  // Favorites
  addFavorite: (data) => axios.post(`${API}/favorites`, data),
  getFavorites: (userId) => axios.get(`${API}/favorites/${userId}`),
  removeFavorite: (favoriteId) => axios.delete(`${API}/favorites/${favoriteId}`),

  // Share
  createShare: (userId) => axios.post(`${API}/share/create?user_id=${userId}`),
  getShare: (shareId) => axios.get(`${API}/share/${shareId}`),
};
