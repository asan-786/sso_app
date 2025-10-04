const axios = require("axios");

const BASE_URL = "http://127.0.0.1:3000";
const CLIENT_ID = "my-app";
/**
 * Initialize SDK with configuration
 */
function init({ baseUrl, clientId }) {
  BASE_URL = baseUrl;
  CLIENT_ID = clientId;
}

/**
 * Login user with email & password
 */
async function login(email, password) {
  try {
    const res = await axios.post(`${BASE_URL}/auth/login`, { email, password, clientId: CLIENT_ID });
    return res.data;
  } catch (error) {
    throw error.response ? error.response.data : error;
  }
}

/**
 * Verify OTP for user
 */
async function verifyOTP(email, otp) {
  try {
    const res = await axios.post(`${BASE_URL}/auth/verify-otp`, { email, otp, clientId: CLIENT_ID });
    return res.data;
  } catch (error) {
    throw error.response ? error.response.data : error;
  }
}

/**
 * Fetch user profile using token
 */
async function getUserProfile(token) {
  try {
    const res = await axios.get(`${BASE_URL}/auth/profile`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return res.data;
  } catch (error) {
    throw error.response ? error.response.data : error;
  }
}

/**
 * Logout user and invalidate session
 */
async function logout(token) {
  try {
    const res = await axios.post(`${BASE_URL}/auth/logout`, {}, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return res.data;
  } catch (error) {
    throw error.response ? error.response.data : error;
  }
}

module.exports = { init, login, verifyOTP, getUserProfile, logout };