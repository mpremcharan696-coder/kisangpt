/**
 * KrishiMitra AI - Frontend Controller
 * =====================================
 * Manages:
 * 1. Top-Middle Menu Navigation (Farm Geolocation & Parameters vs KrishiMitra Voice Chatbot)
 * 2. Farm Geolocation & Farmer Parameters persistence (/api/farm-profile)
 * 3. Environmental Intelligence (Google Earth Engine Soil Texture & Open-Meteo Weather)
 * 4. Location-Specific AI Crop Recommendation System (/api/crop-recommendations)
 * 5. Instant synchronization with KrishiMitra Chatbot Memory
 */

document.addEventListener("DOMContentLoaded", () => {
    // Karnataka Districts Reference Coordinates
    const KARNATAKA_DISTRICTS = {
        "Bagalkote": { lat: 16.1691, lon: 75.6615 },
        "Ballari": { lat: 15.1394, lon: 76.9214 },
        "Belagavi": { lat: 15.8497, lon: 74.4977 },
        "Bengaluru Rural": { lat: 13.2257, lon: 77.5750 },
        "Bengaluru Urban": { lat: 12.9716, lon: 77.5946 },
        "Bidar": { lat: 17.9104, lon: 77.5199 },
        "Chamarajanagara": { lat: 11.9261, lon: 76.9437 },
        "Chikkaballapura": { lat: 13.4325, lon: 77.7275 },
        "Chikkamagaluru": { lat: 13.3161, lon: 75.7720 },
        "Chitradurga": { lat: 14.2251, lon: 76.3980 },
        "Dakshina Kannada": { lat: 12.8703, lon: 74.8806 },
        "Davanagere": { lat: 14.4644, lon: 75.9218 },
        "Dharwad": { lat: 15.4589, lon: 75.0078 },
        "Gadag": { lat: 15.4316, lon: 75.6355 },
        "Hassan": { lat: 13.0072, lon: 76.1029 },
        "Haveri": { lat: 14.7954, lon: 75.3991 },
        "Kalaburagi": { lat: 17.3297, lon: 76.8343 },
        "Kodagu": { lat: 12.4244, lon: 75.7382 },
        "Kolar": { lat: 13.1367, lon: 78.1291 },
        "Koppal": { lat: 15.3468, lon: 76.1557 },
        "Mandya": { lat: 12.5229, lon: 76.8978 },
        "Mysuru": { lat: 12.2958, lon: 76.6394 },
        "Raichur": { lat: 16.2120, lon: 77.3439 },
        "Ramanagara": { lat: 12.7209, lon: 77.2799 },
        "Shivamogga": { lat: 13.9299, lon: 75.5681 },
        "Tumakuru": { lat: 13.3392, lon: 77.1017 },
        "Udupi": { lat: 13.3409, lon: 74.7421 },
        "Uttara Kannada": { lat: 14.7937, lon: 74.5540 },
        "Vijayapura": { lat: 16.8302, lon: 75.7100 },
        "Vijayanagara": { lat: 15.2689, lon: 76.3909 },
        "Yadgir": { lat: 16.7628, lon: 77.1442 }
    };

    // Application State
    const appState = {
        farmerName: "Farmer",
        farmerPhone: "9876543210",
        stateName: "Karnataka",
        districtName: "Dharwad",
        latitude: 15.4589,
        longitude: 75.0078,
        acres: 2.0,
        irrigation: "Borewell / Irrigated",
        plantingMonth: "June",
        farmingGoal: "Maximize Net Profit",
        soilType: null,
        weatherSummary: null,
        environmentalData: null,
        recommendations: null,
        lastSaved: null
    };

    // --- TOP-MIDDLE NAVIGATION MENU LOGIC ---
    const menuBtnLocation = document.getElementById("menuBtnLocation");
    const menuBtnChatbot = document.getElementById("menuBtnChatbot");
    const sectionLocation = document.getElementById("section-location");
    const sectionChatbot = document.getElementById("section-chatbot");

    function switchSection(targetId) {
        if (targetId === "section-chatbot") {
            if (sectionLocation) sectionLocation.style.display = "none";
            if (sectionChatbot) sectionChatbot.style.display = "block";
            if (menuBtnChatbot) menuBtnChatbot.classList.add("active");
            if (menuBtnLocation) menuBtnLocation.classList.remove("active");
            localStorage.setItem("krishimitra_active_menu", "section-chatbot");
        } else {
            if (sectionChatbot) sectionChatbot.style.display = "none";
            if (sectionLocation) sectionLocation.style.display = "block";
            if (menuBtnLocation) menuBtnLocation.classList.add("active");
            if (menuBtnChatbot) menuBtnChatbot.classList.remove("active");
            localStorage.setItem("krishimitra_active_menu", "section-location");
        }
    }

    // Expose global switcher for crop card buttons
    window.switchDashboardTab = (targetId) => {
        switchSection(targetId);
    };

    if (menuBtnLocation) {
        menuBtnLocation.addEventListener("click", () => switchSection("section-location"));
    }
    if (menuBtnChatbot) {
        menuBtnChatbot.addEventListener("click", () => switchSection("section-chatbot"));
    }

    // Restore last active section (default: location)
    const savedActiveTab = localStorage.getItem("krishimitra_active_menu") || "section-location";
    switchSection(savedActiveTab);

    // --- DOM Elements - Form ---
    const inputFarmerName = document.getElementById("inputFarmerName");
    const inputFarmerPhone = document.getElementById("inputFarmerPhone");
    const selectState = document.getElementById("selectState");
    const selectDistrict = document.getElementById("selectDistrict");
    const inputLat = document.getElementById("inputLat");
    const inputLon = document.getElementById("inputLon");
    const inputAcres = document.getElementById("inputAcres");
    const inputIrrigation = document.getElementById("inputIrrigation");
    const selectPlantingMonth = document.getElementById("selectPlantingMonth");
    const selectFarmingGoal = document.getElementById("selectFarmingGoal");

    // Action Buttons
    const btnDetectLocation = document.getElementById("btnDetectLocation");
    const btnAnalyzeFarm = document.getElementById("btnAnalyzeFarm");
    const btnReloadProfile = document.getElementById("btnReloadProfile");
    const locationAlert = document.getElementById("locationAlert");

    // Header Badges
    const headerLocationBadge = document.getElementById("headerLocationBadge");
    const headerDatabaseBadge = document.getElementById("headerDatabaseBadge");
    const syncStatusBadge = document.getElementById("syncStatusBadge");

    // Stored Profile Card
    const storedProfileCard = document.getElementById("storedProfileCard");
    const dbRecordIdBadge = document.getElementById("dbRecordIdBadge");
    const storedFarmerName = document.getElementById("storedFarmerName");
    const storedFarmerPhone = document.getElementById("storedFarmerPhone");
    const storedRegion = document.getElementById("storedRegion");
    const storedCoords = document.getElementById("storedCoords");
    const storedAcresIrrigation = document.getElementById("storedAcresIrrigation");
    const storedTimestamp = document.getElementById("storedTimestamp");

    // Environmental Results Elements
    const envResultsGrid = document.getElementById("envResultsGrid");
    const locationEmptyPrompt = document.getElementById("locationEmptyPrompt");
    const resVillage = document.getElementById("resVillage");
    const resDistrict = document.getElementById("resDistrict");
    const resState = document.getElementById("resState");
    const resDisplayLocation = document.getElementById("resDisplayLocation");
    const resSoilType = document.getElementById("resSoilType");
    const resSoilSource = document.getElementById("resSoilSource");
    const resSoilNote = document.getElementById("resSoilNote");
    const resSeason = document.getElementById("resSeason");
    const resRain = document.getElementById("resRain");
    const resTemp = document.getElementById("resTemp");

    // Crop Recommendations Container Elements
    const cropRecsContainer = document.getElementById("cropRecsContainer");
    const recsCountBadge = document.getElementById("recsCountBadge");
    const recsSummaryBanner = document.getElementById("recsSummaryBanner");
    const cropCardsGrid = document.getElementById("cropCardsGrid");

    // --- Helper: Show Alert Messages ---
    function showAlert(message, type = "info") {
        if (!locationAlert) return;
        locationAlert.className = `badge ${type}`;
        locationAlert.style.display = "block";
        locationAlert.style.padding = "10px 16px";
        locationAlert.style.borderRadius = "8px";
        locationAlert.style.fontSize = "13px";
        locationAlert.style.width = "100%";
        locationAlert.style.textAlign = "left";
        locationAlert.textContent = message;
    }

    // --- Populate Karnataka Districts Dropdown ---
    if (selectDistrict) {
        selectDistrict.innerHTML = '<option value="">-- Choose Karnataka District --</option>';
        Object.keys(KARNATAKA_DISTRICTS).sort().forEach(dist => {
            const opt = document.createElement("option");
            opt.value = dist;
            opt.textContent = dist;
            if (dist === "Dharwad") opt.selected = true;
            selectDistrict.appendChild(opt);
        });

        selectDistrict.addEventListener("change", (e) => {
            const dist = e.target.value;
            if (dist && KARNATAKA_DISTRICTS[dist]) {
                const coords = KARNATAKA_DISTRICTS[dist];
                inputLat.value = coords.lat.toFixed(4);
                inputLon.value = coords.lon.toFixed(4);
                appState.latitude = coords.lat;
                appState.longitude = coords.lon;
                appState.districtName = dist;
                showAlert(`📍 Set coordinates for ${dist}: ${coords.lat.toFixed(4)}°N, ${coords.lon.toFixed(4)}°E`, "info");
            }
        });
    }

    // --- Live Location Synchronization Service ---
    async function syncLiveLocation(lat, lon, isAutomatic = false) {
        if (!isAutomatic) {
            showAlert("🛰️ Querying live GPS: Fetching Earth Engine soil, Open-Meteo climate & AI crops...", "info");
        }
        if (btnDetectLocation) {
            btnDetectLocation.disabled = true;
            btnDetectLocation.textContent = "⏳ Fetching Live Location...";
        }

        inputLat.value = lat.toFixed(4);
        inputLon.value = lon.toFixed(4);
        appState.latitude = lat;
        appState.longitude = lon;

        const sessionId = localStorage.getItem("krishimitra_chat_session_id") || "farmer_session_default";
        const acres = parseFloat(inputAcres.value) || 2.0;
        const irrigation = inputIrrigation ? inputIrrigation.value : "Borewell / Irrigated";
        const plantingMonth = selectPlantingMonth ? selectPlantingMonth.value : "June";
        const farmingGoal = selectFarmingGoal ? selectFarmingGoal.value : "Maximize Net Profit";
        const farmerName = inputFarmerName ? inputFarmerName.value.trim() : "Farmer";

        try {
            const resp = await fetch("/api/sync-live-location", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    latitude: lat,
                    longitude: lon,
                    acres: acres,
                    session_id: sessionId,
                    irrigation: irrigation,
                    planting_month: plantingMonth,
                    farming_goal: farmingGoal,
                    farmer_name: farmerName
                })
            });

            if (!resp.ok) {
                throw new Error(`Live sync failed with status ${resp.status}`);
            }

            const data = await resp.json();
            const loc = data.detected_location || {};
            const env = data.recommendations ? data.recommendations.environmental : null;

            // Automatically select/add detected district in dropdown
            if (loc.district && selectDistrict) {
                appState.districtName = loc.district;
                let foundDistrict = false;
                for (let i = 0; i < selectDistrict.options.length; i++) {
                    if (selectDistrict.options[i].value.toLowerCase() === loc.district.toLowerCase()) {
                        selectDistrict.selectedIndex = i;
                        foundDistrict = true;
                        break;
                    }
                }
                if (!foundDistrict && loc.district) {
                    const opt = document.createElement("option");
                    opt.value = loc.district;
                    opt.textContent = `📍 ${loc.district} (Live Detected)`;
                    opt.selected = true;
                    selectDistrict.appendChild(opt);
                }
            }

            if (loc.state && selectState) {
                selectState.value = loc.state;
            }

            // Render live environmental results
            if (env) {
                renderEnvironmentalResults(env);
            }

            // Render live crop recommendations
            if (data.recommendations) {
                renderCropRecommendations(data.recommendations);
            }

            // Update header badges
            if (headerLocationBadge) {
                const area = loc.village ? `${loc.village}, ${loc.district}` : loc.district || "Live GPS";
                headerLocationBadge.textContent = `📍 Live: ${area}`;
            }
            if (headerDatabaseBadge) {
                headerDatabaseBadge.textContent = "💾 Live Synced";
            }
            if (syncStatusBadge) {
                syncStatusBadge.textContent = "⚡ Live GPS & Climate Synced";
                syncStatusBadge.className = "badge success";
            }

            // Display success alert
            const villageStr = loc.village ? `in ${loc.village}, ` : "";
            showAlert(`✅ Live Location Synced: ${villageStr}${loc.district} (${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E) | Soil: ${data.soil_type} | Temp: ${data.temperature} | Chatbot Memory Synced!`, "success");

            // Dispatch custom event to notify voice assistant memory badges
            window.dispatchEvent(new CustomEvent("krishimitra:memory_updated", { detail: data.memory }));

        } catch (err) {
            console.error("Live sync error:", err);
            showAlert(`Live location sync warning: ${err.message}. Coordinates set to ${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E.`, "warning");
        } finally {
            if (btnDetectLocation) {
                btnDetectLocation.disabled = false;
                btnDetectLocation.textContent = "🛰️ Detect & Sync Live Location";
            }
        }
    }

    // --- Detect Live GPS Location via Browser ---
    if (btnDetectLocation) {
        btnDetectLocation.addEventListener("click", () => {
            if (!navigator.geolocation) {
                showAlert("Geolocation is not supported by your browser.", "warning");
                return;
            }

            showAlert("📡 Querying device GPS sensors for live location...", "info");
            btnDetectLocation.disabled = true;
            btnDetectLocation.textContent = "🛰️ Reading GPS...";

            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    syncLiveLocation(pos.coords.latitude, pos.coords.longitude, false);
                },
                (err) => {
                    btnDetectLocation.disabled = false;
                    btnDetectLocation.textContent = "🛰️ Detect & Sync Live Location";
                    showAlert(`GPS Detection Warning: ${err.message}. Please select your district or verify GPS permissions.`, "warning");
                },
                { enableHighAccuracy: true, timeout: 9000 }
            );
        });
    }

    // --- Render Environmental Intelligence Results ---
    function renderEnvironmentalResults(envData) {
        if (!envData) return;
        if (envResultsGrid) envResultsGrid.style.display = "grid";
        if (locationEmptyPrompt) locationEmptyPrompt.style.display = "none";

        const admin = envData.administrative || envData.admin || {};
        if (resVillage) resVillage.textContent = admin.village || "Local Area";
        if (resDistrict) resDistrict.textContent = admin.district || "District";
        if (resState) resState.textContent = admin.state || "Karnataka";
        if (resDisplayLocation) resDisplayLocation.textContent = admin.display_name || "";

        const soil = envData.soil || {};
        if (resSoilType) resSoilType.textContent = soil.soil_type || "Loam";
        if (resSoilSource) resSoilSource.textContent = soil.source || "Google Earth Engine (250m)";
        if (resSoilNote) resSoilNote.textContent = soil.note || "Satellite-derived USDA soil texture class.";

        const weather = envData.weather_summary || envData.weather || {};
        if (resSeason) resSeason.textContent = weather.current_season || "Kharif";
        if (resRain) resRain.textContent = (weather.forecast_next_7_days_rain_mm !== undefined) ? weather.forecast_next_7_days_rain_mm : "0";
        if (resTemp) {
            const maxT = weather.avg_max_temperature_c || 30;
            const minT = weather.avg_min_temperature_c || 20;
            resTemp.textContent = `${minT}°C – ${maxT}`;
        }
    }

    // --- Render AI Crop Recommendations Cards ---
    function renderCropRecommendations(recsData) {
        if (!recsData || !cropRecsContainer) return;

        cropRecsContainer.style.display = "block";
        const cropsList = recsData.top_recommendations || recsData.recommendations || [];
        
        if (recsCountBadge) {
            recsCountBadge.textContent = `${cropsList.length} Viable Crops Evaluated`;
        }

        if (recsSummaryBanner) {
            const summary = recsData.summary_text || 
                `Based on your farm's verified ${recsData.soil_evaluated || "regional"} soil texture, current seasonal window, and water access, the following crops have been evaluated with agronomic packages of practice.`;
            recsSummaryBanner.textContent = summary;
        }

        if (!cropCardsGrid) return;
        cropCardsGrid.innerHTML = "";

        if (cropsList.length === 0) {
            cropCardsGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 20px;">No crop recommendations available for this query.</div>`;
            return;
        }

        cropsList.forEach(c => {
            const card = document.createElement("div");
            card.className = "crop-card";

            const cropName = c.crop || "Crop";
            const kannadaName = c.kannada_name || "";
            const suitability = c.suitability || "Potentially Suitable";
            const isHigh = suitability.toLowerCase().includes("high");
            const badgeClass = isHigh ? "crop-badge high" : "crop-badge moderate";
            const duration = c.duration_days || "90-120 days";
            const waterNeeds = c.water_needs || "Moderate";
            const reasons = Array.isArray(c.reasons) ? c.reasons : [c.reasons || "Suitable for regional climate."];
            const risks = Array.isArray(c.risks) ? c.risks : [c.risks || "Standard pest monitoring required."];

            card.innerHTML = `
                <div class="crop-card-header">
                    <div>
                        <div class="crop-card-title">${cropName}</div>
                        ${kannadaName ? `<div class="crop-kannada-name">${kannadaName}</div>` : ""}
                    </div>
                    <span class="${badgeClass}">${suitability}</span>
                </div>

                <div class="crop-meta-row">
                    <span>⏱️ <strong>Duration:</strong> ${duration}</span>
                    <span>💧 <strong>Water:</strong> ${waterNeeds}</span>
                </div>

                <div class="crop-section-title">🌱 Agronomic Evidence</div>
                <ul class="crop-reasons-list">
                    ${reasons.map(r => `<li>${r}</li>`).join("")}
                </ul>

                ${risks.length > 0 && risks[0] ? `
                    <div class="crop-risks-box">
                        <strong>⚠️ Key Consideration:</strong> ${risks[0]}
                    </div>
                ` : ""}

                <button class="btn-ask-bot" data-crop="${cropName}">
                    💬 Ask KrishiMitra Voice Assistant about ${cropName}
                </button>
            `;

            // Action button: send question to voice chatbot and switch tab!
            const askBtn = card.querySelector(".btn-ask-bot");
            if (askBtn) {
                askBtn.addEventListener("click", () => {
                    const promptText = `ನನ್ನ ಹೊಲದಲ್ಲಿ ${kannadaName || cropName} ಬೆಳೆಯಲು ಬಿತ್ತನೆ ಕಾಲ, ಗೊಬ್ಬರ ಮತ್ತು ನೀರಿನ ನಿರ್ವಹಣೆ ಹೇಗೆ ಮಾಡಬೇಕು? (How to manage sowing, fertilizer, and irrigation for ${cropName}?)`;
                    switchSection("section-chatbot");
                    
                    // Trigger chatbot message
                    const inputChat = document.getElementById("inputUserChat");
                    const btnSend = document.getElementById("btnSendChat");
                    if (inputChat) {
                        inputChat.value = promptText;
                        if (btnSend) setTimeout(() => btnSend.click(), 250);
                    }
                });
            }

            cropCardsGrid.appendChild(card);
        });
    }

    // --- Save & Analyze Farm Location (Full Workflow) ---
    if (btnAnalyzeFarm) {
        btnAnalyzeFarm.addEventListener("click", async () => {
            const lat = parseFloat(inputLat.value);
            const lon = parseFloat(inputLon.value);
            const acres = parseFloat(inputAcres.value);
            const irrigation = inputIrrigation.value;
            const farmerName = inputFarmerName.value.trim() || "Farmer";
            const farmerPhone = inputFarmerPhone.value.trim() || "";
            const stateName = selectState.value;
            const districtName = selectDistrict.value || "Dharwad";
            const plantingMonth = selectPlantingMonth ? selectPlantingMonth.value : "June";
            const farmingGoal = selectFarmingGoal ? selectFarmingGoal.value : "Maximize Net Profit";
            const sessionId = localStorage.getItem("krishimitra_chat_session_id") || "farmer_session_default";

            if (isNaN(lat) || isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
                showAlert("Please enter valid Latitude (-90 to 90) and Longitude (-180 to 180).", "danger");
                return;
            }

            if (isNaN(acres) || acres <= 0) {
                showAlert("Cultivable Area must be a positive number of acres.", "danger");
                return;
            }

            btnAnalyzeFarm.disabled = true;
            btnAnalyzeFarm.textContent = "⏳ Analyzing Environmental Data & Crops...";
            showAlert("🛰️ Querying Google Earth Engine (soil), Open-Meteo (weather) & AI Recommendation Engine...", "info");

            try {
                // 1. Query Crop Recommendations & Environmental Intelligence
                const recsPayload = {
                    session_id: sessionId,
                    latitude: lat,
                    longitude: lon,
                    acres: acres,
                    irrigation: irrigation,
                    district: districtName,
                    state: stateName,
                    planting_month: plantingMonth,
                    farming_goal: farmingGoal
                };

                const recsRes = await fetch("/api/crop-recommendations", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(recsPayload)
                });

                if (!recsRes.ok) {
                    throw new Error(`Crop recommendation failed with status ${recsRes.status}`);
                }

                const recsData = await recsRes.json();
                const envData = recsData.environmental || {};

                appState.latitude = lat;
                appState.longitude = lon;
                appState.acres = acres;
                appState.irrigation = irrigation;
                appState.farmerName = farmerName;
                appState.farmerPhone = farmerPhone;
                appState.stateName = stateName;
                appState.districtName = districtName;
                appState.plantingMonth = plantingMonth;
                appState.farmingGoal = farmingGoal;
                appState.environmentalData = envData;
                appState.recommendations = recsData;
                appState.soilType = envData.soil ? envData.soil.soil_type : null;
                appState.weatherSummary = envData.weather_summary || null;

                // 2. Persist to SQLite Database (/api/farm-profile)
                const savePayload = {
                    full_name: farmerName,
                    phone_number: farmerPhone,
                    state: stateName,
                    district: districtName,
                    latitude: lat,
                    longitude: lon,
                    acres: acres,
                    irrigation: irrigation,
                    soil_type: appState.soilType,
                    weather_summary: appState.weatherSummary,
                    environmental_data: envData
                };

                const saveRes = await fetch("/api/farm-profile", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(savePayload)
                });

                const saveResult = await saveRes.json();

                // 3. Update localStorage & UI Displays
                localStorage.setItem("krishimitra_farm_profile", JSON.stringify(saveResult.profile || savePayload));
                renderStoredProfileCard(saveResult.profile || savePayload);
                renderEnvironmentalResults(envData);
                renderCropRecommendations(recsData);

                if (headerLocationBadge) {
                    const place = (envData.administrative && envData.administrative.district) ? envData.administrative.district : districtName;
                    headerLocationBadge.textContent = `📍 Location: ${place}, ${stateName}`;
                }
                if (headerDatabaseBadge) {
                    headerDatabaseBadge.textContent = `💾 Profile #${saveResult.profile ? saveResult.profile.id : 1} Synced`;
                }
                if (syncStatusBadge) {
                    syncStatusBadge.textContent = "✅ SQLite Synchronized";
                    syncStatusBadge.className = "badge success";
                }

                showAlert("✅ Farm location, soil data, weather & AI crop recommendations successfully analyzed and synchronized!", "success");

            } catch (err) {
                console.error("Analysis error:", err);
                showAlert(`Error: ${err.message}`, "danger");
            } finally {
                btnAnalyzeFarm.disabled = false;
                btnAnalyzeFarm.textContent = "🌾 Save & Analyze Farm Location (Get Recommendations)";
            }
        });
    }

    // --- Render Stored Profile Card ---
    function renderStoredProfileCard(profile) {
        if (!storedProfileCard) return;

        storedProfileCard.style.display = "block";
        if (dbRecordIdBadge) {
            dbRecordIdBadge.textContent = `Record ID: #${profile.id || 1}`;
        }
        if (storedFarmerName) {
            storedFarmerName.textContent = profile.full_name || "Farmer";
        }
        if (storedFarmerPhone) {
            storedFarmerPhone.textContent = profile.phone_number || "Not specified";
        }
        if (storedRegion) {
            storedRegion.textContent = `${profile.district || "Dharwad"}, ${profile.state || "Karnataka"}`;
        }
        if (storedCoords) {
            const lat = (profile.latitude !== undefined && profile.latitude !== null) ? Number(profile.latitude).toFixed(4) : "15.4589";
            const lon = (profile.longitude !== undefined && profile.longitude !== null) ? Number(profile.longitude).toFixed(4) : "75.0078";
            storedCoords.textContent = `${lat}°N, ${lon}°E`;
        }
        if (storedAcresIrrigation) {
            storedAcresIrrigation.textContent = `${profile.acres || 2.0} Acres (${profile.irrigation || "Borewell / Irrigated"})`;
        }
        if (storedTimestamp) {
            storedTimestamp.textContent = profile.updated_at || new Date().toLocaleString();
        }
    }

    // --- Load Persisted Profile from Backend ---
    async function loadPersistedProfile(showAlertBanner = false) {
        try {
            const res = await fetch("/api/farm-profile");
            if (res.ok) {
                const data = await res.json();
                if (data.status === "success" && data.profile) {
                    const prof = data.profile;
                    if (inputFarmerName) inputFarmerName.value = prof.full_name || "Farmer";
                    if (inputFarmerPhone) inputFarmerPhone.value = prof.phone_number || "";
                    if (selectState && prof.state) selectState.value = prof.state;
                    if (selectDistrict && prof.district) selectDistrict.value = prof.district;
                    if (inputLat && prof.latitude) inputLat.value = Number(prof.latitude).toFixed(4);
                    if (inputLon && prof.longitude) inputLon.value = Number(prof.longitude).toFixed(4);
                    if (inputAcres && prof.acres) inputAcres.value = prof.acres;
                    if (inputIrrigation && prof.irrigation) inputIrrigation.value = prof.irrigation;

                    renderStoredProfileCard(prof);
                    if (prof.environmental_data) {
                        renderEnvironmentalResults(prof.environmental_data);
                    }

                    if (showAlertBanner) {
                        showAlert(`✅ Loaded active profile #${prof.id} (${prof.district}, ${prof.acres} acres) from SQLite database.`, "success");
                    }
                }
            }
        } catch (err) {
            console.warn("Could not fetch remote profile:", err);
        }
    }

    if (btnReloadProfile) {
        btnReloadProfile.addEventListener("click", () => {
            loadPersistedProfile(true);
        });
    }

    // Auto-detect live GPS location on initial launch
    function autoDetectOnStartup() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    syncLiveLocation(pos.coords.latitude, pos.coords.longitude, true);
                },
                (err) => {
                    console.log("Auto-GPS deferred:", err.message);
                    loadPersistedProfile(false);
                },
                { enableHighAccuracy: true, timeout: 5000 }
            );
        } else {
            loadPersistedProfile(false);
        }
    }

    autoDetectOnStartup();
});
