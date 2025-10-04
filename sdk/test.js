const ssoSDK = require("./index");   // Import SDK

// Initialize SDK with backend base URL and clientId
ssoSDK.init({
  baseUrl: "http://127.0.0.1:3000",   // 🔹 Replace with your backend running URL
  clientId: "my-app"                  // 🔹 Replace with your app/client id
});

async function run() {
  try {
    // Step 1: Login user
    const loginRes = await ssoSDK.login("test@example.com", "mypassword");
    console.log("✅ Login Response:", loginRes);

    // Step 2: Verify OTP (example OTP: 123456)
    const otpRes = await ssoSDK.verifyOTP("test@example.com", "123456");
    console.log("✅ OTP Verified:", otpRes);

    // Step 3: Get User Profile
    const profile = await ssoSDK.getUserProfile(otpRes.token);
    console.log("✅ User Profile:", profile);

    // Step 4: Logout
    const logoutRes = await ssoSDK.logout(otpRes.token);
    console.log("✅ Logged Out:", logoutRes);

  } catch (err) {
    console.error("❌ Error:", err);
  }
}

run();
