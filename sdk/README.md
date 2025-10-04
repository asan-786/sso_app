# SSO SDK

This SDK allows third-party applications to integrate with the **University SSO System**.

---

## Installation
```bash
npm install sso-sdk
```

## Initialization
```js
const ssoSDK = require("sso-sdk");

ssoSDK.init({
  baseUrl: "http://localhost:5000",
  clientId: "my-app"
});
```

## Usage

### 🔑 Login
```js
const loginRes = await ssoSDK.login("user@example.com", "mypassword");
console.log(loginRes);
```

### 📧 Verify OTP
```js
const otpRes = await ssoSDK.verifyOTP("user@example.com", "123456");
console.log(otpRes);
```

### 👤 Get User Profile
```js
const profile = await ssoSDK.getUserProfile(otpRes.token);
console.log(profile);
```

### 🚪 Logout
```js
await ssoSDK.logout(otpRes.token);
```

---

✅ This completes **Module 4: SDK Development**.  
You can now place this `/sdk` folder inside your `sso_app` repo.
