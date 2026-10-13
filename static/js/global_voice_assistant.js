/**
 * global_voice_assistant.js
 * =========================
 * Universal Floating Background Voice Assistant for KrishiMitra AI.
 * 
 * Features:
 * 1. Present on EVERY page without changing or reloading the user's current page.
 * 2. Background speech recognition listening for the 'hello' / 'namaskara' wake-word.
 * 3. On-click floating mic button to start/stop speaking anytime.
 * 4. Dual Kannada & English text display + Sarvam AI high-fidelity voice playback.
 * 5. Automatic visual disease guide display when required.
 */

(function () {
    "use strict";

    // Ensure session ID is initialized
    let sessionId = localStorage.getItem("krishimitra_chat_session_id");
    if (!sessionId) {
        sessionId = "farmer_session_" + Math.random().toString(36).substring(2, 10);
        localStorage.setItem("krishimitra_chat_session_id", sessionId);
    }

    let speakingLang = localStorage.getItem("krishimitra_speaking_lang") || "Kannada";
    let isListeningActive = false;
    let isProcessing = false;
    let isSpeaking = false;
    let recognizer = null;
    let activeAudio = null;
    let isWakeWordMode = true;

    // Wake-word keywords regex
    const WAKE_WORD_REGEX = /\b(hello|namaskara|namaste|hey krishi|hello krishi|krishimitra)\b/i;

    // --- Inject Floating Widget DOM into Current Page ---
    function injectWidgetDOM() {
        if (document.getElementById("globalVoiceContainer")) return;

        const container = document.createElement("div");
        container.id = "globalVoiceContainer";
        container.className = "global-voice-container";

        container.innerHTML = `
            <!-- Floating Assistant Window Card -->
            <div id="globalVoiceCard" class="global-voice-card">
                <div class="voice-card-header">
                    <div class="voice-card-title-group">
                        <span style="font-size: 18px;">🌱</span>
                        <div>
                            <div class="voice-card-title">KrishiMitra Voice AI</div>
                            <span class="voice-card-badge" id="voiceCardLangBadge">${speakingLang}</span>
                        </div>
                    </div>
                    <div class="voice-card-actions">
                        <button type="button" class="voice-btn-icon" id="btnMinimizeVoice" title="Minimize">✕</button>
                    </div>
                </div>

                <div class="voice-card-body">
                    <!-- Status Banner with Waveform -->
                    <div id="voiceStatusBanner" class="voice-status-banner">
                        <div class="voice-wave-container">
                            <span class="voice-wave-bar"></span>
                            <span class="voice-wave-bar"></span>
                            <span class="voice-wave-bar"></span>
                            <span class="voice-wave-bar"></span>
                        </div>
                        <span id="voiceStatusText">Say "Hello" or tap mic to speak</span>
                    </div>

                    <!-- Transcript & Response Box -->
                    <div id="voiceTranscriptBox" class="voice-transcript-box">
                        <div class="transcript-user">
                            <span>You said:</span>
                            <div id="voiceUserText" style="font-style: italic; color: #475569;">"Hello KrishiMitra"</div>
                        </div>
                        <div style="border-top: 1px solid #e2e8f0; padding-top: 6px; margin-top: 6px;">
                            <div id="voiceBotKn" class="transcript-bot-kn">ನಮಸ್ಕಾರ! ನಿಮ್ಮ ಕೃಷಿ, ಬೆಳೆ ಅಥವಾ ರೋಗಗಳ ಬಗ್ಗೆ ಕೇಳಿ.</div>
                            <div id="voiceBotEn" class="transcript-bot-en">Hello! Ask me about your crops, weather, or pest care.</div>
                        </div>
                    </div>

                    <!-- Pictorial Visual Guide Preview Box -->
                    <div id="voiceVisualBox" class="voice-visual-preview" style="display: none;">
                        <img id="voiceVisualImg" src="" alt="Agricultural Visual Guide">
                        <div id="voiceVisualCaption" class="voice-visual-caption"></div>
                    </div>
                </div>

                <div class="voice-card-footer">
                    <button type="button" id="btnToggleListening" class="voice-btn-mic-toggle">
                        <span id="micToggleIcon">🎙️</span>
                        <span id="micToggleLabel">Tap to Speak</span>
                    </button>
                    <div class="voice-hint-keyword">
                        Say <strong>"Hello"</strong> anytime
                    </div>
                </div>
            </div>

            <!-- Floating Action Button (FAB) -->
            <button type="button" id="globalVoiceFab" class="global-voice-fab is-wake-active" title="KrishiMitra Voice Assistant (Say 'Hello' or Click)">
                <span id="fabIcon">🎙️</span>
                <span id="fabDot" class="global-voice-dot"></span>
            </button>
        `;

        document.body.appendChild(container);
        wireWidgetEvents();
    }

    // --- Wire Widget UI Events ---
    function wireWidgetEvents() {
        const fab = document.getElementById("globalVoiceFab");
        const card = document.getElementById("globalVoiceCard");
        const btnMinimize = document.getElementById("btnMinimizeVoice");
        const btnToggle = document.getElementById("btnToggleListening");

        if (fab) {
            fab.addEventListener("click", () => {
                const isOpen = card.classList.contains("open");
                if (!isOpen) {
                    openVoiceCard();
                    startActiveListening();
                } else {
                    if (isListeningActive) {
                        stopActiveListening();
                    } else {
                        startActiveListening();
                    }
                }
            });
        }

        if (btnMinimize) {
            btnMinimize.addEventListener("click", () => {
                closeVoiceCard();
            });
        }

        if (btnToggle) {
            btnToggle.addEventListener("click", () => {
                if (isListeningActive) {
                    stopActiveListening();
                } else {
                    startActiveListening();
                }
            });
        }
    }

    function openVoiceCard() {
        const card = document.getElementById("globalVoiceCard");
        if (card) card.classList.add("open");
    }

    function closeVoiceCard() {
        const card = document.getElementById("globalVoiceCard");
        if (card) card.classList.remove("open");
        if (activeAudio) {
            activeAudio.pause();
        }
    }

    // --- Update UI Status Helpers ---
    function updateStatus(text, state = "idle") {
        const banner = document.getElementById("voiceStatusBanner");
        const statusText = document.getElementById("voiceStatusText");
        const fab = document.getElementById("globalVoiceFab");
        const fabDot = document.getElementById("fabDot");
        const btnToggle = document.getElementById("btnToggleListening");
        const micToggleLabel = document.getElementById("micToggleLabel");

        if (statusText) statusText.textContent = text;
        if (banner) {
            banner.className = `voice-status-banner ${state}`;
        }

        if (fab) {
            if (state === "listening") {
                fab.classList.add("is-listening");
            } else {
                fab.classList.remove("is-listening");
            }
        }

        if (fabDot) {
            if (state === "listening") {
                fabDot.className = "global-voice-dot listening";
            } else {
                fabDot.className = "global-voice-dot";
            }
        }

        if (btnToggle && micToggleLabel) {
            if (state === "listening") {
                btnToggle.classList.add("is-listening");
                micToggleLabel.textContent = "Listening... Tap to Stop";
            } else {
                btnToggle.classList.remove("is-listening");
                micToggleLabel.textContent = "Tap to Speak";
            }
        }
    }

    // --- Speech Recognition & Wake-Word Detection ---
    function initSpeechEngine() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn("[KrishiMitra Voice] SpeechRecognition is not supported in this browser.");
            return;
        }

        try {
            recognizer = new SpeechRecognition();
            recognizer.continuous = true;
            recognizer.interimResults = true;
            recognizer.lang = (speakingLang === "English") ? "en-IN" : "kn-IN";

            recognizer.onstart = () => {
                console.log("[KrishiMitra Voice] Background speech engine active.");
            };

            recognizer.onresult = (event) => {
                let interimTranscript = "";
                let finalTranscript = "";

                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += transcript;
                    } else {
                        interimTranscript += transcript;
                    }
                }

                const spokenText = (finalTranscript || interimTranscript).trim();
                if (!spokenText) return;

                console.log("[KrishiMitra Voice Heard]:", spokenText);

                // Check for 'Hello' keyword trigger
                if (WAKE_WORD_REGEX.test(spokenText)) {
                    console.log("[KrishiMitra Voice] 🌟 'Hello' wake-word detected!");
                    openVoiceCard();

                    // Strip wake word from query if question followed
                    const cleanedQuery = spokenText.replace(WAKE_WORD_REGEX, "").trim();

                    if (cleanedQuery.length > 3) {
                        // User said "Hello, what crop should I sow?"
                        processFarmerQuery(cleanedQuery);
                    } else {
                        // User just said "Hello"
                        updateStatus("Heard 'Hello'! Listening for your farming query...", "listening");
                        playWakeAcknowledgement();
                    }
                    return;
                }

                // If in active query listening mode
                if (isListeningActive && finalTranscript.trim().length > 2) {
                    processFarmerQuery(finalTranscript.trim());
                }
            };

            recognizer.onerror = (err) => {
                if (err.error !== "no-speech") {
                    console.warn("[KrishiMitra Voice Recognition Error]:", err.error);
                }
            };

            recognizer.onend = () => {
                // Keep background listening alive for 'Hello' keyword
                if (isWakeWordMode && !isSpeaking && !isProcessing) {
                    try {
                        setTimeout(() => {
                            if (isWakeWordMode && !isSpeaking && !isProcessing) {
                                recognizer.start();
                            }
                        }, 600);
                    } catch (_) {}
                }
            };

            // Start background listening
            recognizer.start();

        } catch (e) {
            console.warn("[KrishiMitra Voice] Could not auto-start speech recognition:", e);
        }
    }

    // --- Audio Feedback for 'Hello' Wake-Word ---
    function playWakeAcknowledgement() {
        const wakeText = (speakingLang === "English") 
            ? "Hello! KrishiMitra is listening. How can I help?" 
            : "ನಮಸ್ಕಾರ! ಕೃಷಿಮಿತ್ರ ಕೇಳಿಸಿಕೊಳ್ಳುತ್ತಿದೆ. ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಹೇಳಿ.";
        
        speakText(wakeText, (speakingLang === "English") ? "en-IN" : "kn-IN", () => {
            startActiveListening();
        });
    }

    function startActiveListening() {
        isListeningActive = true;
        openVoiceCard();
        updateStatus("🟢 Listening... Speak your farming question now", "listening");

        try {
            if (recognizer) {
                recognizer.lang = (speakingLang === "English") ? "en-IN" : "kn-IN";
                recognizer.start();
            }
        } catch (_) {}
    }

    function stopActiveListening() {
        isListeningActive = false;
        updateStatus("Say 'Hello' or tap mic to speak", "idle");
    }

    // --- Send Farmer Query to /api/chat/message in Background ---
    async function processFarmerQuery(queryText) {
        if (isProcessing) return;
        isProcessing = true;
        isListeningActive = false;

        const userTextEl = document.getElementById("voiceUserText");
        if (userTextEl) userTextEl.textContent = `"${queryText}"`;

        updateStatus("⏳ KrishiMitra AI is thinking...", "idle");

        try {
            const res = await fetch("/api/chat/message", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: sessionId,
                    message: queryText,
                    preferred_language: speakingLang,
                    voice_speaker: "kavya",
                    voice_pace: 1.0
                })
            });

            if (!res.ok) {
                throw new Error(`Chat error status ${res.status}`);
            }

            const data = await res.json();
            displayAndSpeakReply(data);

            // Notify dashboard of any memory updates
            if (data.total_memory) {
                window.dispatchEvent(new CustomEvent("krishimitra:memory_updated", { detail: data.total_memory }));
            }

        } catch (err) {
            console.error("[KrishiMitra Voice Error]:", err);
            updateStatus("Could not process voice request. Please try again.", "idle");
        } finally {
            isProcessing = false;
        }
    }

    // --- Display Reply & Speak Aloud ---
    function displayAndSpeakReply(data) {
        const botKnEl = document.getElementById("voiceBotKn");
        const botEnEl = document.getElementById("voiceBotEn");
        const visualBox = document.getElementById("voiceVisualBox");
        const visualImg = document.getElementById("voiceVisualImg");
        const visualCaption = document.getElementById("voiceVisualCaption");

        if (botKnEl) botKnEl.textContent = data.kannada_reply || "";
        if (botEnEl) botEnEl.textContent = data.english_reply || "";

        // Display visual card if present
        if (data.visual_aid && (data.visual_aid.image_url || data.visual_aid.image_base64)) {
            if (visualBox && visualImg) {
                visualImg.src = data.visual_aid.image_base64 || data.visual_aid.image_url;
                if (visualCaption) {
                    visualCaption.textContent = data.visual_aid.caption_kannada || data.visual_aid.caption_english || "ಚಿತ್ರ: ಕೃಷಿ ಮಾಹಿತಿ";
                }
                visualBox.style.display = "block";
            }
        } else if (visualBox) {
            visualBox.style.display = "none";
        }

        // Determine audio source (Sarvam AI base64 or client TTS)
        const activeLang = data.active_speaking_language || speakingLang;
        const textToSpeak = (activeLang === "English") ? data.english_reply : data.kannada_reply;
        const langCode = (activeLang === "English") ? "en-IN" : "kn-IN";
        const audioB64 = (activeLang === "English") 
            ? (data.audio_english_base64 || data.audio_base64) 
            : (data.audio_kannada_base64 || data.audio_base64);

        updateStatus("🔊 KrishiMitra is speaking...", "speaking");
        isSpeaking = true;

        if (audioB64) {
            playBase64Audio(audioB64, () => {
                isSpeaking = false;
                updateStatus("Say 'Hello' or tap mic to speak", "idle");
            });
        } else {
            speakText(textToSpeak, langCode, () => {
                isSpeaking = false;
                updateStatus("Say 'Hello' or tap mic to speak", "idle");
            });
        }
    }

    function playBase64Audio(base64Data, onEndCallback) {
        try {
            if (activeAudio) activeAudio.pause();
            activeAudio = new Audio("data:audio/wav;base64," + base64Data);
            activeAudio.onended = () => {
                if (onEndCallback) onEndCallback();
            };
            activeAudio.onerror = () => {
                if (onEndCallback) onEndCallback();
            };
            activeAudio.play();
        } catch (_) {
            if (onEndCallback) onEndCallback();
        }
    }

    function speakText(text, langCode, onEndCallback) {
        if (!("speechSynthesis" in window)) {
            if (onEndCallback) onEndCallback();
            return;
        }

        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = langCode;
        utterance.rate = 1.0;
        utterance.onend = () => {
            if (onEndCallback) onEndCallback();
        };
        utterance.onerror = () => {
            if (onEndCallback) onEndCallback();
        };
        window.speechSynthesis.speak(utterance);
    }

    // --- Initialize on Page Load ---
    document.addEventListener("DOMContentLoaded", () => {
        injectWidgetDOM();
        initSpeechEngine();
    });

})();
