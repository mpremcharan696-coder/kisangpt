/**
 * auth.js
 * =======
 * Firebase Modular Authentication for KrishiMitra AI.
 * Supports:
 * 1. Google One-Click Sign-In (Popup)
 * 2. Email & Password (Sign-In & Registration)
 * 3. Phone Number Verification (SMS OTP + reCAPTCHA)
 */

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import {
    getAuth,
    GoogleAuthProvider,
    signInWithPopup,
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    updateProfile,
    sendPasswordResetEmail,
    RecaptchaVerifier,
    signInWithPhoneNumber,
    onAuthStateChanged
} from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";

// Exact Firebase project configuration provided by user
const firebaseConfig = {
    apiKey: "AIzaSyB-3u_10pQWLj6HE9-nTEkYu-z4bs3zyL8",
    authDomain: "auth-f826f.firebaseapp.com",
    projectId: "auth-f826f",
    storageBucket: "auth-f826f.firebasestorage.app",
    messagingSenderId: "888053285644",
    appId: "1:888053285644:web:1aac406ab14eaeabe7bf29",
    measurementId: "G-2EQ1H7NRFX"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// Global state for phone OTP
let confirmationResult = null;
let recaptchaVerifier = null;
let isSignUpMode = false;

// DOM Elements
const alertBox = document.getElementById("authAlert");
const btnGoogleAuth = document.getElementById("btnGoogleAuth");

// Tab Elements
const tabEmailBtn = document.getElementById("tabEmailBtn");
const tabPhoneBtn = document.getElementById("tabPhoneBtn");
const emailPanel = document.getElementById("email-panel");
const phonePanel = document.getElementById("phone-panel");

// Email Form Elements
const subToggleSignIn = document.getElementById("subToggleSignIn");
const subToggleSignUp = document.getElementById("subToggleSignUp");
const emailAuthForm = document.getElementById("emailAuthForm");
const groupDisplayName = document.getElementById("groupDisplayName");
const displayNameInput = document.getElementById("displayNameInput");
const emailInput = document.getElementById("emailInput");
const passwordInput = document.getElementById("passwordInput");
const btnEmailSubmit = document.getElementById("btnEmailSubmit");
const emailSubmitLabel = document.getElementById("emailSubmitLabel");
const emailSpinner = document.getElementById("emailSpinner");
const linkForgotPassword = document.getElementById("linkForgotPassword");

// Phone Form Elements
const phoneSendOtpForm = document.getElementById("phoneSendOtpForm");
const phoneVerifyOtpForm = document.getElementById("phoneVerifyOtpForm");
const phoneNumberInput = document.getElementById("phoneNumberInput");
const btnSendOtp = document.getElementById("btnSendOtp");
const phoneSpinner = document.getElementById("phoneSpinner");
const displayTargetPhone = document.getElementById("displayTargetPhone");
const otpCodeInput = document.getElementById("otpCodeInput");
const btnVerifyOtp = document.getElementById("btnVerifyOtp");
const verifySpinner = document.getElementById("verifySpinner");
const btnChangeNumber = document.getElementById("btnChangeNumber");

// Helper: Show Alert
function showAlert(message, type = "danger") {
    if (!alertBox) return;
    alertBox.className = `auth-alert ${type}`;
    alertBox.textContent = message;
    alertBox.classList.remove("hidden");
    alertBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function clearAlert() {
    if (!alertBox) return;
    alertBox.className = "auth-alert hidden";
    alertBox.textContent = "";
}

// Redirect if already authenticated
onAuthStateChanged(auth, (user) => {
    if (user) {
        // Store user identifier in localStorage for dashboard memory sync
        const farmerName = user.displayName || (user.email ? user.email.split("@")[0] : user.phoneNumber) || "Farmer";
        localStorage.setItem("farmer_auth_user", JSON.stringify({
            uid: user.uid,
            name: farmerName,
            email: user.email || "",
            phone: user.phoneNumber || "",
            photoURL: user.photoURL || ""
        }));
        
        // Redirect to dashboard
        window.location.href = "/dashboard";
    }
});

// ─── 1. Google One-Click Sign-In ──────────────────────────────────────────────
if (btnGoogleAuth) {
    btnGoogleAuth.addEventListener("click", async () => {
        clearAlert();
        try {
            btnGoogleAuth.disabled = true;
            const provider = new GoogleAuthProvider();
            provider.setCustomParameters({ prompt: 'select_account' });
            
            await signInWithPopup(auth, provider);
            showAlert("Signed in successfully with Google! Redirecting...", "success");
            // onAuthStateChanged will handle redirection
        } catch (error) {
            console.error("Google Auth Error:", error);
            btnGoogleAuth.disabled = false;
            
            if (error.code === "auth/popup-closed-by-user") {
                showAlert("Google Sign-In popup was closed. Please try again.", "info");
            } else if (error.code === "auth/unauthorized-domain") {
                showAlert("Firebase Domain Notice: Please ensure 127.0.0.1 and localhost are added under Authorized Domains in your Firebase Console.", "danger");
            } else {
                showAlert(`Google Sign-In Error: ${error.message}`, "danger");
            }
        }
    });
}

// ─── Method Tab Switching ───────────────────────────────────────────────────
if (tabEmailBtn && tabPhoneBtn) {
    tabEmailBtn.addEventListener("click", () => {
        clearAlert();
        tabEmailBtn.classList.add("active");
        tabPhoneBtn.classList.remove("active");
        emailPanel.classList.remove("hidden");
        phonePanel.classList.add("hidden");
    });

    tabPhoneBtn.addEventListener("click", () => {
        clearAlert();
        tabPhoneBtn.classList.add("active");
        tabEmailBtn.classList.remove("active");
        phonePanel.classList.remove("hidden");
        emailPanel.classList.add("hidden");
        initRecaptcha();
    });
}

// ─── Email Sign-In vs Create Account Toggle ─────────────────────────────────
if (subToggleSignIn && subToggleSignUp) {
    subToggleSignIn.addEventListener("click", () => {
        clearAlert();
        isSignUpMode = false;
        subToggleSignIn.classList.add("active");
        subToggleSignUp.classList.remove("active");
        groupDisplayName.classList.add("hidden");
        emailSubmitLabel.textContent = "Sign In / ಸೈನ್ ಇನ್";
    });

    subToggleSignUp.addEventListener("click", () => {
        clearAlert();
        isSignUpMode = true;
        subToggleSignUp.classList.add("active");
        subToggleSignIn.classList.remove("active");
        groupDisplayName.classList.remove("hidden");
        emailSubmitLabel.textContent = "Create Account / ಖಾತೆ ರಚಿಸಿ";
    });
}

// ─── 2. Email & Password Form Handling ──────────────────────────────────────
if (emailAuthForm) {
    emailAuthForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        clearAlert();

        const email = emailInput.value.trim();
        const password = passwordInput.value;
        const displayName = displayNameInput ? displayNameInput.value.trim() : "";

        if (!email || !password) {
            showAlert("Please enter both email address and password.", "danger");
            return;
        }

        if (isSignUpMode && password.length < 6) {
            showAlert("Password must be at least 6 characters long.", "danger");
            return;
        }

        try {
            btnEmailSubmit.disabled = true;
            emailSpinner.classList.remove("hidden");

            if (isSignUpMode) {
                // Register new user
                const userCred = await createUserWithEmailAndPassword(auth, email, password);
                if (displayName) {
                    await updateProfile(userCred.user, { displayName: displayName });
                }
                showAlert("Account created successfully! Redirecting to dashboard...", "success");
            } else {
                // Sign in existing user
                await signInWithEmailAndPassword(auth, email, password);
                showAlert("Signed in successfully! Redirecting to dashboard...", "success");
            }
        } catch (error) {
            console.error("Email Auth Error:", error);
            btnEmailSubmit.disabled = false;
            emailSpinner.classList.add("hidden");

            switch (error.code) {
                case "auth/invalid-email":
                    showAlert("Invalid email address format.", "danger");
                    break;
                case "auth/user-not-found":
                    showAlert("No account found with this email. Please click 'Create Account'.", "danger");
                    break;
                case "auth/wrong-password":
                case "auth/invalid-credential":
                    showAlert("Incorrect email or password. Please verify your credentials.", "danger");
                    break;
                case "auth/email-already-in-use":
                    showAlert("This email is already registered. Please sign in or reset your password.", "danger");
                    break;
                case "auth/weak-password":
                    showAlert("Password is too weak. Please use at least 6 characters.", "danger");
                    break;
                default:
                    showAlert(`Authentication Error: ${error.message}`, "danger");
            }
        }
    });
}

// Forgot Password Link
if (linkForgotPassword) {
    linkForgotPassword.addEventListener("click", async (e) => {
        e.preventDefault();
        const email = emailInput.value.trim();
        if (!email) {
            showAlert("Please enter your email address above first, then click 'Forgot?'.", "info");
            emailInput.focus();
            return;
        }

        try {
            await sendPasswordResetEmail(auth, email);
            showAlert(`Password reset link sent to ${email}. Please check your inbox.`, "success");
        } catch (error) {
            showAlert(`Password Reset Error: ${error.message}`, "danger");
        }
    });
}

// ─── 3. Phone Number Verification (SMS OTP) ─────────────────────────────────
function initRecaptcha() {
    if (!recaptchaVerifier) {
        try {
            recaptchaVerifier = new RecaptchaVerifier(auth, "recaptcha-container", {
                size: "invisible",
                callback: () => {
                    // reCAPTCHA solved
                },
                "expired-callback": () => {
                    showAlert("reCAPTCHA expired. Please try sending OTP again.", "info");
                }
            });
            recaptchaVerifier.render();
        } catch (err) {
            console.warn("Recaptcha initialization notice:", err);
        }
    }
}

// Send OTP
if (phoneSendOtpForm) {
    phoneSendOtpForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        clearAlert();

        const rawPhone = phoneNumberInput.value.trim().replace(/\D/g, "");
        if (rawPhone.length !== 10) {
            showAlert("Please enter a valid 10-digit Indian mobile number.", "danger");
            return;
        }

        const fullPhoneNumber = `+91${rawPhone}`;

        try {
            btnSendOtp.disabled = true;
            phoneSpinner.classList.remove("hidden");

            initRecaptcha();
            confirmationResult = await signInWithPhoneNumber(auth, fullPhoneNumber, recaptchaVerifier);
            
            // Switch form to OTP verification step
            phoneSendOtpForm.classList.add("hidden");
            phoneVerifyOtpForm.classList.remove("hidden");
            displayTargetPhone.textContent = `+91 ${rawPhone.slice(0, 5)} ${rawPhone.slice(5)}`;
            showAlert(`Verification code sent via SMS to +91 ${rawPhone}.`, "info");
            otpCodeInput.focus();
        } catch (error) {
            console.error("Phone OTP Send Error:", error);
            btnSendOtp.disabled = false;
            phoneSpinner.classList.add("hidden");

            if (recaptchaVerifier) {
                try { recaptchaVerifier.clear(); recaptchaVerifier = null; } catch (_) {}
            }

            if (error.code === "auth/invalid-phone-number") {
                showAlert("Invalid phone number format.", "danger");
            } else if (error.code === "auth/quota-exceeded") {
                showAlert("SMS quota exceeded. Please try Google Sign-In or Email/Password.", "danger");
            } else {
                showAlert(`SMS OTP Error: ${error.message}`, "danger");
            }
        }
    });
}

// Verify OTP
if (phoneVerifyOtpForm) {
    phoneVerifyOtpForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        clearAlert();

        const otp = otpCodeInput.value.trim().replace(/\D/g, "");
        if (otp.length !== 6) {
            showAlert("Please enter the complete 6-digit verification code.", "danger");
            return;
        }

        if (!confirmationResult) {
            showAlert("Session expired. Please request a new OTP code.", "danger");
            btnChangeNumber.click();
            return;
        }

        try {
            btnVerifyOtp.disabled = true;
            verifySpinner.classList.remove("hidden");

            await confirmationResult.confirm(otp);
            showAlert("Phone number verified successfully! Redirecting...", "success");
            // onAuthStateChanged will redirect
        } catch (error) {
            console.error("Phone OTP Verification Error:", error);
            btnVerifyOtp.disabled = false;
            verifySpinner.classList.add("hidden");

            if (error.code === "auth/invalid-verification-code") {
                showAlert("Incorrect 6-digit code. Please verify the code sent to your phone.", "danger");
            } else if (error.code === "auth/code-expired") {
                showAlert("The code has expired. Please request a new OTP code.", "danger");
            } else {
                showAlert(`Verification Error: ${error.message}`, "danger");
            }
        }
    });
}

// Change Number button handler
if (btnChangeNumber) {
    btnChangeNumber.addEventListener("click", () => {
        clearAlert();
        phoneVerifyOtpForm.classList.add("hidden");
        phoneSendOtpForm.classList.remove("hidden");
        btnSendOtp.disabled = false;
        phoneSpinner.classList.add("hidden");
        phoneNumberInput.focus();
    });
}
