/**
 * voice_assistant.js
 * ==================
 * 1-to-1 Interactive Bilingual (Kannada & English) Voice Assistant for KrishiMitra AI.
 *
 * Enforces single speaking language lock:
 * Uses ONLY 1 language to speak aloud until the user explicitly asks for a change.
 * Stores and renders both replies separately without raw JSON mixing.
 */

document.addEventListener("DOMContentLoaded", () => {
    // --- Session Setup ---
    let sessionId = localStorage.getItem("krishimitra_chat_session_id");
    if (!sessionId) {
        sessionId = "farmer_session_" + Math.random().toString(36).substring(2, 10);
        localStorage.setItem("krishimitra_chat_session_id", sessionId);
    }

    // Active Locked Speaking Language (Default: Kannada)
    let activeSpeakingLanguage = localStorage.getItem("krishimitra_speaking_lang") || "Kannada";

    // --- DOM Elements ---
    const chatStream = document.getElementById("chatStream");
    const inputUserChat = document.getElementById("inputUserChat");
    const btnSendChat = document.getElementById("btnSendChat");
    const btnVoiceMic = document.getElementById("btnVoiceMic");
    const micStatusText = document.getElementById("micStatusText");
    const selectVoiceSpeaker = document.getElementById("selectVoiceSpeaker");
    const selectChatLang = document.getElementById("selectChatLang");
    const rangePace = document.getElementById("rangePace");
    const paceValueLabel = document.getElementById("paceValueLabel");
    const checkAutoSpeak = document.getElementById("checkAutoSpeak");
    const memoryBadgesContainer = document.getElementById("memoryBadgesContainer");

    // Audio Player State
    let currentAudioPlayer = null;
    let isListening = false;
    let speechRecognizer = null;

    // Synchronize UI dropdown with active locked speaking language
    if (selectChatLang) {
        selectChatLang.value = activeSpeakingLanguage;
        selectChatLang.addEventListener("change", (e) => {
            activeSpeakingLanguage = e.target.value;
            localStorage.setItem("krishimitra_speaking_lang", activeSpeakingLanguage);
            if (speechRecognizer) {
                speechRecognizer.lang = (activeSpeakingLanguage === "English") ? "en-IN" : "kn-IN";
            }
        });
    }

    // --- Update Pace Label ---
    if (rangePace && paceValueLabel) {
        rangePace.addEventListener("input", (e) => {
            paceValueLabel.textContent = `${e.target.value}x`;
        });
    }

    // --- Initialize Web Speech Recognition (STT) ---
    function initSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn("Web Speech API not supported in this browser. Fallback to text input.");
            return null;
        }

        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => {
            isListening = true;
            if (btnVoiceMic) btnVoiceMic.classList.add("listening");
            if (micStatusText) {
                const langLabel = (activeSpeakingLanguage === "English") ? "English" : "Kannada (ಕನ್ನಡ)";
                micStatusText.textContent = `🔴 Listening... Speak now in ${langLabel}`;
                micStatusText.style.color = "#dc2626";
            }
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            if (inputUserChat) {
                inputUserChat.value = transcript;
            }
            if (micStatusText) {
                micStatusText.textContent = `Acquired: "${transcript}"`;
                micStatusText.style.color = "#16a34a";
            }
            setTimeout(() => {
                sendMessage(transcript);
            }, 300);
        };

        recognition.onerror = (event) => {
            console.warn("Speech recognition error:", event.error);
            isListening = false;
            if (btnVoiceMic) btnVoiceMic.classList.remove("listening");
            if (micStatusText) {
                micStatusText.textContent = `Mic paused (${event.error}). Tap mic or type message.`;
                micStatusText.style.color = "#6b7280";
            }
        };

        recognition.onend = () => {
            isListening = false;
            if (btnVoiceMic) btnVoiceMic.classList.remove("listening");
            if (micStatusText) {
                micStatusText.textContent = "Tap mic to speak or type your question below";
                micStatusText.style.color = "#6b7280";
            }
        };

        return recognition;
    }

    speechRecognizer = initSpeechRecognition();

    // --- Microphone Button Handler ---
    if (btnVoiceMic) {
        btnVoiceMic.addEventListener("click", () => {
            if (!speechRecognizer) {
                alert("Speech recognition is not supported in this browser. Please use Chrome or Edge, or type your message.");
                return;
            }

            if (isListening) {
                speechRecognizer.stop();
            } else {
                speechRecognizer.lang = (activeSpeakingLanguage === "English") ? "en-IN" : "kn-IN";
                try {
                    speechRecognizer.start();
                } catch (e) {
                    console.error("Mic start error:", e);
                }
            }
        });
    }

    // --- Play Audio Output Helper ---
    function playAudioOutput(base64Audio, fallbackText, langCode = "kn-IN") {
        if (currentAudioPlayer) {
            currentAudioPlayer.pause();
            currentAudioPlayer = null;
        }

        // 1. Play Sarvam AI audio WAV if provided
        if (base64Audio) {
            try {
                const audio = new Audio("data:audio/wav;base64," + base64Audio);
                currentAudioPlayer = audio;
                audio.play().catch(err => {
                    console.warn("Autoplay blocked, user interaction required:", err);
                });
                return;
            } catch (err) {
                console.error("Sarvam audio play error:", err);
            }
        }

        // 2. Fallback to client browser Web Speech API
        if ("speechSynthesis" in window && fallbackText) {
            try {
                window.speechSynthesis.cancel();
                const utter = new SpeechSynthesisUtterance(fallbackText);
                utter.lang = langCode;
                utter.rate = rangePace ? parseFloat(rangePace.value) : 1.0;

                const voices = window.speechSynthesis.getVoices();
                const matchedVoice = voices.find(v => v.lang.startsWith(langCode.substring(0, 2)));
                if (matchedVoice) utter.voice = matchedVoice;

                window.speechSynthesis.speak(utter);
            } catch (err) {
                console.warn("Client TTS error:", err);
            }
        }
    }

    // --- Text Sanitizer (Guarantees NO JSON Syntax Leaks) ---
    function cleanDisplayText(text) {
        if (!text) return "";
        let s = String(text).trim();
        // If string contains raw JSON fragments, strip them
        if (s.includes('"english_reply"') || s.includes('"kannada_reply"')) {
            try {
                const parsed = JSON.parse(s);
                return parsed.kannada_reply || parsed.english_reply || s;
            } catch (e) {
                // Regex fallback
                s = s.replace(/\{?\s*"(?:english|kannada)_reply"\s*:\s*"?/g, '');
                s = s.replace(/"?,\s*"(?:english|kannada)_reply".*$/s, '');
                s = s.replace(/["\}]+$/g, '');
            }
        }
        return s.trim();
    }

    // --- Render Message Bubble in Chat Stream ---
    function appendMessage(sender, data) {
        if (!chatStream) return;

        const msgDiv = document.createElement("div");
        msgDiv.className = `chat-bubble ${sender}`;
        msgDiv.style.marginBottom = "16px";

        if (sender === "user") {
            msgDiv.innerHTML = `
                <div style="display: flex; justify-content: flex-end;">
                    <div style="background: var(--primary); color: #ffffff; padding: 12px 18px; border-radius: 16px 16px 2px 16px; max-width: 80%; font-size: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="font-size: 11px; opacity: 0.85; margin-bottom: 4px;">👤 Farmer</div>
                        <div>${data.text}</div>
                    </div>
                </div>
            `;
        } else {
            // Clean distinct replies
            const kannadaReply = cleanDisplayText(data.kannada_reply);
            const englishReply = cleanDisplayText(data.english_reply);
            const speakingTag = (activeSpeakingLanguage === "English") ? "🔊 Speaking: English" : "🔊 Speaking: ಕನ್ನಡ";

            msgDiv.innerHTML = `
                <div style="display: flex; justify-content: flex-start;">
                    <div style="background: #ffffff; border: 1px solid var(--border); border-left: 5px solid var(--primary); padding: 16px 20px; border-radius: 4px 16px 16px 16px; max-width: 92%; box-shadow: 0 3px 6px rgba(0,0,0,0.06);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;">
                            <strong style="color: var(--primary-dark); font-size: 14px; display: flex; align-items: center; gap: 6px;">
                                🌱 KrishiMitra AI • ಕೃಷಿಮಿತ್ರ
                            </strong>
                            <div style="display: flex; gap: 6px; align-items: center;">
                                <span class="badge success" style="font-size: 11px;">${speakingTag}</span>
                                <span class="badge info" style="font-size: 11px;">🎙️ Sarvam AI</span>
                            </div>
                        </div>

                        <!-- Kannada Reply Block -->
                        <div style="background: #fefce8; border: 1px solid #fef08a; padding: 12px 14px; border-radius: 8px; margin-bottom: 12px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <span style="font-size: 12px; font-weight: 700; color: #854d0e;">🟡 ಕನ್ನಡ (Kannada)</span>
                                <button class="btn btn-secondary btn-sm btn-play-kn" style="padding: 3px 10px; font-size: 11px;">
                                    🔊 ಕೇಳಿ (Listen)
                                </button>
                            </div>
                            <div style="font-size: 14px; line-height: 1.7; color: #1e293b; font-family: 'Noto Sans Kannada', sans-serif;">
                                ${kannadaReply}
                            </div>
                        </div>

                        <!-- English Reply Block -->
                        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; padding: 12px 14px; border-radius: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <span style="font-size: 12px; font-weight: 700; color: #166534;">🟢 English</span>
                                <button class="btn btn-secondary btn-sm btn-play-en" style="padding: 3px 10px; font-size: 11px;">
                                    🔊 Listen English
                                </button>
                            </div>
                            <div style="font-size: 14px; line-height: 1.6; color: #1e293b;">
                                ${englishReply}
                            </div>
                    </div>
                </div>
            `;

            // If pictorial visual aid was generated
            if (data.visual_aid && (data.visual_aid.image_url || data.visual_aid.image_base64)) {
                const imgSource = data.visual_aid.image_base64 || data.visual_aid.image_url;
                const visualCard = document.createElement("div");
                visualCard.style.cssText = "margin-top: 12px; border-radius: 10px; overflow: hidden; border: 1px solid #cbd5e1; background: #ffffff; box-shadow: 0 2px 8px rgba(0,0,0,0.06);";
                visualCard.innerHTML = `
                    <img src="${imgSource}" 
                         alt="Agricultural Visual Guide" 
                         style="width: 100%; max-height: 280px; object-fit: cover; display: block;" 
                         loading="lazy" />
                    <div style="padding: 10px 14px; background: #f8fafc; border-top: 1px solid #e2e8f0;">
                        <div style="font-weight: 700; color: #15803d; font-size: 13px; font-family: 'Noto Sans Kannada', sans-serif;">
                            🖼️ ${data.visual_aid.caption_kannada || "ಚಿತ್ರ: ಕೃಷಿ ಮಾಹಿತಿ ವಿವರಣೆ"}
                        </div>
                        <div style="color: #64748b; font-size: 11.5px; margin-top: 3px;">
                            ${data.visual_aid.caption_english || "Visual: Agricultural reference guide"}
                        </div>
                    </div>
                `;
                const container = msgDiv.querySelector(".bot-bilingual-container");
                if (container) container.appendChild(visualCard);
            }


            // On-demand Voice Playback handlers
            const btnPlayKn = msgDiv.querySelector(".btn-play-kn");
            const btnPlayEn = msgDiv.querySelector(".btn-play-en");

            if (btnPlayKn) {
                btnPlayKn.addEventListener("click", async () => {
                    btnPlayKn.textContent = "⏳ Generating...";
                    await requestAndPlayVoice(kannadaReply, "kn-IN");
                    btnPlayKn.textContent = "🔊 ಕೇಳಿ (Listen)";
                });
            }

            if (btnPlayEn) {
                btnPlayEn.addEventListener("click", async () => {
                    btnPlayEn.textContent = "⏳ Generating...";
                    await requestAndPlayVoice(englishReply, "en-IN");
                    btnPlayEn.textContent = "🔊 Listen English";
                });
            }
        }

        chatStream.appendChild(msgDiv);
        chatStream.scrollTop = chatStream.scrollHeight;
    }

    // --- Request Sarvam Voice Synthesis on Demand ---
    async function requestAndPlayVoice(text, langCode) {
        const speaker = selectVoiceSpeaker ? selectVoiceSpeaker.value : "kavya";
        const pace = rangePace ? parseFloat(rangePace.value) : 1.0;

        try {
            const res = await fetch("/api/voice/speak", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    text: text,
                    language_code: langCode,
                    speaker: speaker,
                    pace: pace
                })
            });

            const data = await res.json();
            playAudioOutput(data.audio_base64, text, langCode);
        } catch (err) {
            console.warn("Sarvam voice request failed, using client TTS:", err);
            playAudioOutput(null, text, langCode);
        }
    }

    // --- Update Conversational Memory Badges ---
    function updateMemoryBadges(memory) {
        if (!memoryBadgesContainer) return;
        memoryBadgesContainer.innerHTML = "";

        if (!memory || Object.keys(memory).length === 0) {
            memoryBadgesContainer.innerHTML = `
                <span class="badge warning" style="font-size: 11.5px; padding: 4px 10px; cursor: pointer; display: inline-flex; align-items: center; gap: 5px;" onclick="window.switchDashboardTab('section-location'); document.getElementById('btnDetectLocation').click();">
                    🛰️ Live Location: Tap here to detect GPS & sync real soil & temperature
                </span>
            `;
            return;
        }

        const iconMap = {
            district: "📍",
            soil_type: "🌱",
            temperature: "🌡️",
            recommended_crops: "🌾",
            acres: "📐",
            irrigation: "💧",
            crop: "🌿",
            preferred_language: "🗣️"
        };

        const keys = Object.keys(memory);
        let renderedCount = 0;

        keys.forEach(k => {
            const val = memory[k];
            if (val !== null && val !== undefined && String(val).trim() !== "") {
                const icon = iconMap[k] || "📌";
                const badge = document.createElement("span");
                badge.className = "badge info";
                badge.style.fontSize = "11px";
                badge.style.padding = "3px 8px";

                let displayVal = val;
                if (Array.isArray(val)) {
                    displayVal = val.join(", ");
                } else if (typeof val === "string" && val.startsWith("[") && val.endsWith("]")) {
                    try {
                        const parsedArr = JSON.parse(val);
                        if (Array.isArray(parsedArr)) displayVal = parsedArr.join(", ");
                    } catch (_) {}
                }

                badge.textContent = `${icon} ${k}: ${displayVal}`;
                memoryBadgesContainer.appendChild(badge);
                renderedCount++;
            }
        });

        if (renderedCount === 0) {
            memoryBadgesContainer.innerHTML = `
                <span class="badge warning" style="font-size: 11.5px; padding: 4px 10px; cursor: pointer;" onclick="window.switchDashboardTab('section-location'); document.getElementById('btnDetectLocation').click();">
                    🛰️ Live Location: Tap to sync live GPS, soil & climate
                </span>
            `;
        }
    }

    // --- Send Chat Message ---
    async function sendMessage(text) {
        const msgText = (text || (inputUserChat ? inputUserChat.value : "")).trim();
        if (!msgText) return;

        if (inputUserChat) inputUserChat.value = "";

        appendMessage("user", { text: msgText });

        const thinkingDiv = document.createElement("div");
        thinkingDiv.id = "thinkingIndicator";
        thinkingDiv.style.marginBottom = "14px";
        thinkingDiv.innerHTML = `
            <div style="display: inline-flex; align-items: center; gap: 8px; background: #f8fafc; padding: 8px 16px; border-radius: 12px; font-size: 12px; color: var(--text-muted); border: 1px solid var(--border);">
                <div class="spinner" style="width: 14px; height: 14px; border-width: 2px;"></div>
                <span>ಕೃಷಿಮಿತ್ರ AI ಯೋಚಿಸುತ್ತಿದೆ... Generating bilingual replies...</span>
            </div>
        `;
        chatStream.appendChild(thinkingDiv);
        chatStream.scrollTop = chatStream.scrollHeight;

        const speaker = selectVoiceSpeaker ? selectVoiceSpeaker.value : "kavya";
        const pace = rangePace ? parseFloat(rangePace.value) : 1.0;

        try {
            const res = await fetch("/api/chat/message", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: sessionId,
                    message: msgText,
                    preferred_language: activeSpeakingLanguage,
                    voice_speaker: speaker,
                    voice_pace: pace
                })
            });

            const data = await res.json();
            if (thinkingDiv && thinkingDiv.parentNode) thinkingDiv.remove();

            if (res.ok && data.status === "success") {
                // If language switch was detected, update locked speaking language
                if (data.active_speaking_language) {
                    activeSpeakingLanguage = data.active_speaking_language;
                    localStorage.setItem("krishimitra_speaking_lang", activeSpeakingLanguage);
                    if (selectChatLang) selectChatLang.value = activeSpeakingLanguage;
                }

                appendMessage("bot", {
                    kannada_reply: data.kannada_reply,
                    english_reply: data.english_reply,
                    intent: data.intent,
                    visual_aid: data.visual_aid
                });

                if (data.total_memory) {
                    updateMemoryBadges(data.total_memory);
                }

                // Strictly speak in ONLY the 1 locked active language until user asks for a change
                const autoSpeak = checkAutoSpeak ? checkAutoSpeak.checked : true;
                if (autoSpeak) {
                    if (activeSpeakingLanguage === "English") {
                        playAudioOutput(data.audio_base64, data.english_reply, "en-IN");
                    } else {
                        playAudioOutput(data.audio_base64, data.kannada_reply, "kn-IN");
                    }
                }
            } else {
                throw new Error(data.error || "Message delivery failed");
            }
        } catch (err) {
            console.error("Chat error:", err);
            if (thinkingDiv && thinkingDiv.parentNode) thinkingDiv.remove();
            appendMessage("bot", {
                kannada_reply: "ಕ್ಷಮಿಸಿ, ದೋಷ ಸಂಭವಿಸಿದೆ. ದಯವಿಟ್ಟು ಇನ್ನೊಮ್ಮೆ ಪ್ರಯತ್ನಿಸಿ.",
                english_reply: `Sorry, an error occurred: ${err.message}. Please try again.`
            });
        }
    }

    // --- Onboarding Initial Greeting Flow ---
    async function triggerOnboardingGreeting() {
        const speaker = selectVoiceSpeaker ? selectVoiceSpeaker.value : "kavya";
        const pace = rangePace ? parseFloat(rangePace.value) : 1.0;

        try {
            const res = await fetch("/api/chat/onboarding", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: sessionId,
                    voice_speaker: speaker,
                    voice_pace: pace,
                    preferred_language: activeSpeakingLanguage
                })
            });

            if (res.ok) {
                const data = await res.json();
                appendMessage("bot", {
                    kannada_reply: data.kannada_reply,
                    english_reply: data.english_reply,
                    intent: "onboarding"
                });

                // Auto-speak onboarding greeting in strictly 1 locked speaking language (Default: Kannada)
                const autoSpeak = checkAutoSpeak ? checkAutoSpeak.checked : true;
                if (autoSpeak) {
                    if (activeSpeakingLanguage === "English") {
                        playAudioOutput(data.audio_english_base64 || data.audio_base64, data.english_reply, "en-IN");
                    } else {
                        playAudioOutput(data.audio_kannada_base64 || data.audio_base64, data.kannada_reply, "kn-IN");
                    }
                }
            }
        } catch (err) {
            console.warn("Onboarding greeting fetch error:", err);
        }
    }

    // --- Event Listeners ---
    if (btnSendChat) {
        btnSendChat.addEventListener("click", () => sendMessage());
    }

    if (inputUserChat) {
        inputUserChat.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                sendMessage();
            }
        });
    }

    // Refresh Assistant Memory from SQLite
    async function refreshAssistantMemory() {
        try {
            const res = await fetch(`/api/chat/history?session_id=${sessionId}`);
            if (res.ok) {
                const data = await res.json();
                if (data.memory) {
                    updateMemoryBadges(data.memory);
                }
            }
        } catch (e) {
            console.warn("Could not refresh memory:", e);
        }
    }

    const menuBtnChatbotEl = document.getElementById("menuBtnChatbot");
    if (menuBtnChatbotEl) {
        menuBtnChatbotEl.addEventListener("click", () => {
            refreshAssistantMemory();
        });
    }

    // Listen for real-time live location memory updates dispatched from dashboard
    window.addEventListener("krishimitra:memory_updated", (e) => {
        if (e.detail) {
            updateMemoryBadges(e.detail);
        } else {
            refreshAssistantMemory();
        }
    });

    // Initial memory refresh
    refreshAssistantMemory();

    // Start Onboarding Greeting on launch
    triggerOnboardingGreeting();
});


