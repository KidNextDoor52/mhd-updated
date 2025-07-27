
# MHD Mobile App (React Native)

This is the mobile companion app for the MHD platform, built with React Native (Expo).

## 📲 Features
- JWT-based login to FastAPI backend
- Dashboard view of uploaded documents
- Form submission workflow
- Profile view
- Secure share link support

## 🚀 Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Start the App
```bash
npx expo start
```

Use Expo Go on your phone to scan the QR code.

### 3. Configure Backend
Update the backend base URL in `utils/config.js`:

```js
export const BASE_URL = "http://<your-ip>:8000";
```

Make sure your phone is on the same Wi-Fi network as your dev machine.

---

## 🛠 Screens

- `LoginScreen.js` – handles authentication
- `DashboardScreen.js` – shows document + form list
- `FormScreen.js` – create new medical forms
- `ProfileScreen.js` – view user info

---

## 🔐 Auth
On successful login, JWT is saved to AsyncStorage and used for authenticated requests.

---

## 📦 Built with:
- React Native (Expo)
- React Navigation
- Axios
- AsyncStorage

