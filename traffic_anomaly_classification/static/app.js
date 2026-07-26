// CosmosGuard Dashboard Javascript Engine
window.addEventListener('error', (event) => {
    fetch('/api/log-error', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            message: event.message,
            source: event.filename,
            lineno: event.lineno,
            colno: event.colno,
            error: event.error ? event.error.stack : null
        })
    });
});

document.addEventListener("DOMContentLoaded", () => {
    // UI Elements
    const videoPlayer = document.getElementById("videoPlayer");
    const videoPlaceholder = document.getElementById("videoPlaceholder");
    const analysisLoader = document.getElementById("analysisLoader");
    const dropZone = document.getElementById("dropZone");
    const fileInput = document.getElementById("fileInput");
    const selectFileBtn = document.getElementById("selectFileBtn");
    
    // Video HUD elements
    const videoHud = document.getElementById("videoHud");
    const scannerLine = document.getElementById("scannerLine");
    const scannerText = document.getElementById("scannerText");
    const detectionBox = document.getElementById("detectionBox");
    const detectionBoxLabel = document.getElementById("detectionBoxLabel");
    const hudCard = document.getElementById("hudCard");
    const hudCardDot = document.getElementById("hudCardDot");
    const hudCardTitle = document.getElementById("hudCardTitle");
    const hudInfoLabel = document.getElementById("hudInfoLabel");
    const hudInfoScore = document.getElementById("hudInfoScore");
    const hudInfoMode = document.getElementById("hudInfoMode");

    // Status Badge & Indicators
    const modeBadge = document.getElementById("modeBadge");
    const statusIndicator = document.getElementById("statusIndicator");
    const statusLabel = document.getElementById("statusLabel");
    
    // Sidebar Elements
    const settingsSidebar = document.getElementById("settingsSidebar");
    const sidebarOverlay = document.getElementById("sidebarOverlay");
    const toggleSettingsBtn = document.getElementById("toggleSettingsBtn");
    const closeSettingsBtn = document.getElementById("closeSettingsBtn");
    const settingsForm = document.getElementById("settingsForm");
    const regenerateVideosBtn = document.getElementById("regenerateVideosBtn");
    
    // Form Inputs
    const simModeCheckbox = document.getElementById("simModeCheckbox");
    const apiKeyInput = document.getElementById("apiKeyInput");
    const apiEndpointInput = document.getElementById("apiEndpointInput");
    
    // Threshold sliders & value labels
    const thresholds = {
        accident: { el: document.getElementById("thresholdAccident"), val: document.getElementById("thresholdAccidentVal") },
        fight: { el: document.getElementById("thresholdFight"), val: document.getElementById("thresholdFightVal") },
        obstacle: { el: document.getElementById("thresholdObstacle"), val: document.getElementById("thresholdObstacleVal") },
        violation: { el: document.getElementById("thresholdViolation"), val: document.getElementById("thresholdViolationVal") }
    };
    
    // Dynamic Charts & Logs
    const chartsContainer = document.getElementById("chartsContainer");
    const logsTableBody = document.getElementById("logsTableBody");
    const clearLogsBtn = document.getElementById("clearLogsBtn");
    
    // Anomaly labels list to send to the backend
    const LABELS = [
        "Normal Trafik Akışı",
        "Trafik Kazası / Çarpışma",
        "Kavga / Fiziksel Müdahale",
        "Yoldaki Engel / Duran Araç",
        "Kural İhlali (Kırmızı Işık/Hız/Hatalı Şerit)"
    ];
    
    // Local configuration cache
    let currentConfig = {
        simulation_mode: true,
        thresholds: { accident: 0.4, fight: 0.4, obstacle: 0.4, violation: 0.4 }
    };
    
    // Log System State
    let detectionLogs = [];
    
    // Active detection state for video HUD
    let activeDetection = {
        isAnomaly: false,
        detectedLabel: "",
        source: "",
        maxScore: 0
    };
    
    // Initialize
    setupEventListeners();
    loadConfig();
    loadLogs();
    
    // Setup Event Listeners
    function setupEventListeners() {
        // Toggle Sidebar
        toggleSettingsBtn.addEventListener("click", openSidebar);
        closeSettingsBtn.addEventListener("click", closeSidebar);
        sidebarOverlay.addEventListener("click", closeSidebar);
        
        // Connect slider change events
        Object.keys(thresholds).forEach(key => {
            thresholds[key].el.addEventListener("input", (e) => {
                thresholds[key].val.textContent = parseFloat(e.target.value).toFixed(2);
            });
        });
        
        // Settings form submit
        settingsForm.addEventListener("submit", saveConfig);
        
        // Regenerate synthetic videos
        regenerateVideosBtn.addEventListener("click", regenerateVideos);
        
        // Drag & Drop events
        dropZone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropZone.classList.add("dragover");
        });
        
        dropZone.addEventListener("dragleave", () => {
            dropZone.classList.remove("dragover");
        });
        
        dropZone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropZone.classList.remove("dragover");
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFileSelect(files[0]);
            }
        });
        
        // File select button
        selectFileBtn.addEventListener("click", () => fileInput.click());
        fileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) {
                handleFileSelect(e.target.files[0]);
            }
        });
        
        // Preset Scenario click events
        document.querySelectorAll(".scenario-item").forEach(item => {
            item.addEventListener("click", () => {
                // Clear active states
                document.querySelectorAll(".scenario-item").forEach(i => i.classList.remove("active"));
                item.classList.add("active");
                
                const sampleName = item.getAttribute("data-sample");
                const friendlyName = item.getAttribute("data-name");
                
                loadSampleVideo(sampleName, friendlyName);
            });
        });
        
        // Clear logs
        clearLogsBtn.addEventListener("click", clearLogs);
        
        // Video player HUD update during playback
        videoPlayer.addEventListener("timeupdate", updateHudOverlay);
    }
    
    // Open/Close Sidebar
    function openSidebar() {
        settingsSidebar.classList.add("open");
        sidebarOverlay.classList.add("active");
    }
    
    function closeSidebar() {
        settingsSidebar.classList.remove("open");
        sidebarOverlay.classList.remove("active");
    }
    
    // Fetch Configuration from API
    async function loadConfig() {
        try {
            const response = await fetch("/api/config");
            const data = await response.json();
            currentConfig = data;
            
            // Populate form
            simModeCheckbox.checked = data.simulation_mode;
            apiEndpointInput.value = data.api_endpoint;
            if (data.has_api_key) {
                apiKeyInput.value = "******" + data.api_key_masked;
            } else {
                apiKeyInput.value = "";
            }
            
            // Set thresholds sliders
            if (data.thresholds) {
                Object.keys(thresholds).forEach(key => {
                    if (data.thresholds[key] !== undefined) {
                        thresholds[key].el.value = data.thresholds[key];
                        thresholds[key].val.textContent = parseFloat(data.thresholds[key]).toFixed(2);
                    }
                });
            }
            
            updateModeBadge(data.simulation_mode);
        } catch (err) {
            console.error("Konfigürasyon yüklenemedi:", err);
            showNotification("Sistem yapılandırması yüklenirken bir hata oluştu.", "danger");
        }
    }
    
    // Save Configuration
    async function saveConfig(e) {
        e.preventDefault();
        
        const payload = {
            simulation_mode: simModeCheckbox.checked,
            api_endpoint: apiEndpointInput.value,
            api_key: apiKeyInput.value,
            thresholds: {
                accident: parseFloat(thresholds.accident.el.value),
                fight: parseFloat(thresholds.fight.el.value),
                obstacle: parseFloat(thresholds.obstacle.el.value),
                violation: parseFloat(thresholds.violation.el.value)
            }
        };
        
        try {
            const response = await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            
            if (result.status === "success") {
                showNotification("Yapılandırma başarıyla kaydedildi.", "success");
                closeSidebar();
                loadConfig(); // Refresh local cache
            } else {
                showNotification("Kaydetme başarısız: " + result.message, "danger");
            }
        } catch (err) {
            console.error("Konfigürasyon kaydedilemedi:", err);
            showNotification("Yapılandırma kaydedilirken hata oluştu.", "danger");
        }
    }
    
    // Regenerate synthetic videos
    async function regenerateVideos() {
        const originalText = regenerateVideosBtn.innerHTML;
        regenerateVideosBtn.disabled = true;
        regenerateVideosBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Üretiliyor...';
        
        try {
            const response = await fetch("/api/generate-samples", { method: "POST" });
            const result = await response.json();
            if (result.status === "success") {
                showNotification("Sentetik videolar başarıyla yeniden üretildi.", "success");
            } else {
                showNotification("Üretim başarısız: " + result.detail, "danger");
            }
        } catch (err) {
            showNotification("Video üretimi sırasında bağlantı hatası oluştu.", "danger");
        } finally {
            regenerateVideosBtn.disabled = false;
            regenerateVideosBtn.innerHTML = originalText;
        }
    }
    
    // Update Mode Badge
    function updateModeBadge(isSim) {
        if (isSim) {
            modeBadge.className = "badge badge-sim";
            modeBadge.querySelector(".badge-text").textContent = "Simülasyon Modu Aktif";
        } else {
            modeBadge.className = "badge badge-live";
            modeBadge.querySelector(".badge-text").textContent = "Canlı API Modu (Cosmos-Embed1)";
        }
    }
    
    // Load Preset Sample Video
    function loadSampleVideo(sampleName, friendlyName) {
        videoPlaceholder.style.display = "none";
        videoPlayer.style.display = "block";
        videoPlayer.src = `/static/samples/${sampleName}`;
        videoPlayer.load();
        videoPlayer.play();
        
        analyzeVideo({ sample_name: sampleName, source_name: friendlyName });
    }
    
    // Handle File Upload Select
    function handleFileSelect(file) {
        if (file.type !== "video/mp4") {
            showNotification("Lütfen yalnızca MP4 formatında video yükleyin.", "warning");
            return;
        }
        
        // Remove active preset item states
        document.querySelectorAll(".scenario-item").forEach(i => i.classList.remove("active"));
        
        videoPlaceholder.style.display = "none";
        videoPlayer.style.display = "block";
        videoPlayer.src = URL.createObjectURL(file);
        videoPlayer.load();
        videoPlayer.play();
        
        analyzeVideo({ file: file, source_name: file.name });
    }
    
    // Analyze Video API Call
    async function analyzeVideo({ file, sample_name, source_name }) {
        analysisLoader.style.display = "flex";
        
        // Reset active detection state
        activeDetection = {
            isAnomaly: false,
            detectedLabel: "",
            source: sample_name || (file ? file.name : ""),
            maxScore: 0
        };
        
        // Reset HUD overlay display
        videoHud.style.display = "block";
        scannerLine.style.display = "block";
        scannerText.style.display = "block";
        detectionBox.style.display = "none";
        hudCard.style.display = "none";
        
        const formData = new FormData();
        formData.append("labels", LABELS.join(","));
        
        if (file) {
            formData.append("video_file", file);
        } else if (sample_name) {
            formData.append("sample_name", sample_name);
        }
        
        try {
            const response = await fetch("/api/analyze", {
                method: "POST",
                body: formData
            });
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Sunucu analizi sırasında hata oluştu.");
            }
            
            const results = await response.json();
            displayResults(results, source_name);
            
        } catch (err) {
            console.error("Analiz hatası:", err);
            showNotification(err.message, "danger");
            resetStatus();
            chartsContainer.innerHTML = `<div class="chart-empty-state text-danger"><i class="fa-solid fa-triangle-exclamation"></i> Analiz tamamlanamadı.<br><small>${err.message}</small></div>`;
            videoHud.style.display = "none";
        } finally {
            analysisLoader.style.display = "none";
            scannerLine.style.display = "none";
            scannerText.style.display = "none";
        }
    }
    
    // Reset status to normal
    function resetStatus() {
        statusIndicator.className = "status-indicator status-normal";
        statusLabel.textContent = "Analiz Bekleniyor";
    }
    
    // Display Results & Update Charts & Badges
    function displayResults(results, sourceName) {
        const scores = results.scores;
        const detected = results.detected;
        const maxScore = results.max_score;
        const mode = results.mode;
        
        // Clear empty state
        chartsContainer.innerHTML = "";
        
        // Define Icon and Color Map for Labels
        const labelStyles = {
            "Normal Trafik Akışı": { icon: "fa-circle-check", class: "normal", thresholdKey: null },
            "Trafik Kazası / Çarpışma": { icon: "fa-car-burst", class: "danger", thresholdKey: "accident" },
            "Kavga / Fiziksel Müdahale": { icon: "fa-people-robbery", class: "danger", thresholdKey: "fight" },
            "Yoldaki Engel / Duran Araç": { icon: "fa-triangle-exclamation", class: "warning", thresholdKey: "obstacle" },
            "Kural İhlali (Kırmızı Işık/Hız/Hatalı Şerit)": { icon: "fa-traffic-light", class: "danger", thresholdKey: "violation" }
        };
        
        // Map detected class to global status banner
        let isAnomalyDetected = false;
        let finalStatusClass = "status-normal";
        let finalStatusText = "Normal Trafik Akışı";
        
        const currentThresholds = currentConfig.thresholds;
        
        // Determine final decision based on thresholds
        const styleInfo = labelStyles[detected];
        if (styleInfo && styleInfo.thresholdKey) {
            const thresholdLimit = currentThresholds[styleInfo.thresholdKey] || 0.40;
            if (maxScore >= thresholdLimit) {
                isAnomalyDetected = true;
                finalStatusClass = styleInfo.class === "danger" ? "status-danger" : "status-warning";
                
                // Formulate status labels
                if (detected.includes("Kaza")) finalStatusText = "Kaza Algılandı!";
                else if (detected.includes("Kavga")) finalStatusText = "Kavga Algılandı!";
                else if (detected.includes("Engel")) finalStatusText = "Yolda Engel Tespit Edildi!";
                else if (detected.includes("Kural")) finalStatusText = "Kural İhlali Tespit Edildi!";
            }
        }
        
        // Update Status indicator
        statusIndicator.className = `status-indicator ${finalStatusClass}`;
        statusLabel.textContent = finalStatusText;
        
        // Render Bars
        LABELS.forEach(label => {
            const score = scores[label] || 0;
            const percentage = Math.min(100, Math.max(0, score * 100)).toFixed(0);
            
            const info = labelStyles[label];
            let fillClass = "fill-normal";
            let thresholdLineHtml = "";
            
            if (info.thresholdKey) {
                const thr = currentThresholds[info.thresholdKey] || 0.40;
                const thrPct = (thr * 100).toFixed(0);
                
                // If it is a threat class
                fillClass = info.class === "danger" ? "fill-danger" : "fill-obstacle";
                thresholdLineHtml = `
                    <div class="threshold-marker" style="left: ${thrPct}%;">
                        <span class="threshold-marker-label" title="Duyarlılık Eşiği: ${thr.toFixed(2)}">${thr.toFixed(2)}</span>
                    </div>
                `;
            }
            
            const barItem = document.createElement("div");
            barItem.className = "chart-bar-item";
            barItem.innerHTML = `
                <div class="chart-label-row">
                    <span class="chart-label-text">
                        <i class="fa-solid ${info.icon} ${info.class || 'success'}-color"></i>
                        <span>${label}</span>
                    </span>
                    <span class="chart-score">${score.toFixed(3)}</span>
                </div>
                <div class="chart-track">
                    ${thresholdLineHtml}
                    <div class="chart-fill ${fillClass}" style="width: ${percentage}%;"></div>
                </div>
            `;
            chartsContainer.appendChild(barItem);
        });
        
        // Update active detection state for HUD tracking
        activeDetection.isAnomaly = isAnomalyDetected;
        activeDetection.detectedLabel = detected;
        activeDetection.maxScore = maxScore;
        
        // Show and configure telemetry HUD card
        hudCard.style.display = "flex";
        
        // Update status dot & left border based on anomaly presence
        if (isAnomalyDetected) {
            const isDanger = styleInfo.class === "danger";
            hudCard.style.borderLeftColor = isDanger ? "var(--danger)" : "var(--warning)";
            hudCardDot.className = `hud-dot ${isDanger ? 'pulsing-red' : 'pulsing-warning'}`;
            hudCardTitle.textContent = isDanger ? "TEHLİKE ALGILANDI" : "SİSTEM UYARISI";
            hudInfoLabel.textContent = detected.split(" / ")[0].split(" (")[0].toUpperCase();
            hudInfoLabel.style.color = isDanger ? "var(--danger)" : "var(--warning)";
        } else {
            hudCard.style.borderLeftColor = "var(--success)";
            hudCardDot.className = "hud-dot pulsing-green";
            hudCardTitle.textContent = "GÜVENLİ DURUM";
            hudInfoLabel.textContent = "NORMAL AKIŞ";
            hudInfoLabel.style.color = "var(--success)";
        }
        hudInfoScore.textContent = (maxScore * 100).toFixed(1) + "%";
        hudInfoMode.textContent = mode === "simulation" ? "SİMÜLASYON" : "CANLI API";
        
        // Trigger immediate overlay refresh
        updateHudOverlay();

        // Add log entry
        addLogEntry({
            timestamp: new Date().toLocaleTimeString(),
            source: sourceName,
            detected: isAnomalyDetected ? detected : "Normal Trafik Akışı",
            score: maxScore,
            isAnomaly: isAnomalyDetected,
            mode: mode === "simulation" ? "Simülasyon" : "Canlı API"
        });
    }

    // Update Video HUD Overlay Bounding Box dynamically
    function updateHudOverlay() {
        if (!activeDetection.isAnomaly || videoPlayer.paused) {
            detectionBox.style.display = "none";
            return;
        }
        
        const src = activeDetection.source.toLowerCase();
        const curTime = videoPlayer.currentTime;
        
        let showBox = false;
        let coords = { top: "30%", left: "30%", width: "40%", height: "40%" }; // default fallback
        let borderClass = "";
        
        if (src.includes("accident") || src.includes("kaza")) {
            // Accident happens after 1.4 seconds
            if (curTime >= 1.4) {
                showBox = true;
                coords = { top: "38%", left: "26%", width: "24%", height: "24%" };
            }
        } else if (src.includes("fight") || src.includes("kavga")) {
            // Fight is active from the beginning/after 0.4s
            if (curTime >= 0.4) {
                showBox = true;
                coords = { top: "42%", left: "3%", width: "16%", height: "28%" };
            }
        } else if (src.includes("obstacle") || src.includes("engel")) {
            // Obstacle is visible immediately
            showBox = true;
            coords = { top: "44%", left: "45%", width: "12%", height: "14%" };
            borderClass = "detection-box-warning";
        } else if (src.includes("violation") || src.includes("ihlal")) {
            // Violation is detected when vehicle crosses stop line at 1.1s
            if (curTime >= 1.1) {
                showBox = true;
                coords = { top: "46%", left: "40%", width: "16%", height: "24%" };
            }
        } else {
            // Uploaded custom videos - show in the center
            showBox = true;
            coords = { top: "30%", left: "30%", width: "40%", height: "40%" };
        }
        
        if (showBox) {
            detectionBox.className = "detection-box " + borderClass;
            detectionBox.style.display = "block";
            detectionBox.style.top = coords.top;
            detectionBox.style.left = coords.left;
            detectionBox.style.width = coords.width;
            detectionBox.style.height = coords.height;
            
            // Format clean label name
            const cleanLabel = activeDetection.detectedLabel.split(" / ")[0].split(" (")[0];
            detectionBoxLabel.textContent = `${cleanLabel} (${(activeDetection.maxScore * 100).toFixed(0)}%)`;
        } else {
            detectionBox.style.display = "none";
        }
    }
    
    function loadLogs() {
        const stored = localStorage.getItem("cosmos_guard_logs");
        if (stored) {
            try {
                detectionLogs = JSON.parse(stored);
                renderLogs();
            } catch (e) {
                detectionLogs = [];
            }
        }
    }
    
    function saveLogs() {
        localStorage.setItem("cosmos_guard_logs", JSON.stringify(detectionLogs));
    }
    
    function addLogEntry(log) {
        // Add to beginning of array
        detectionLogs.unshift(log);
        
        // Keep last 50 logs
        if (detectionLogs.length > 50) {
            detectionLogs.pop();
        }
        
        saveLogs();
        renderLogs();
    }
    
    function renderLogs() {
        if (detectionLogs.length === 0) {
            logsTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="table-empty">Henüz kaydedilmiş anomali bulunmuyor.</td>
                </tr>
            `;
            return;
        }
        
        logsTableBody.innerHTML = "";
        
        detectionLogs.forEach((log) => {
            if (!log) return;
            const tr = document.createElement("tr");
            
            // Source cell formatting
            const sourceStr = log.source || "Bilinmeyen Kaynak";
            const isSample = typeof sourceStr === 'string' && sourceStr.endsWith(".mp4");
            const icon = isSample ? "fa-video" : "fa-file-video";
            
            // Status cell formatting
            let statusBadge = "";
            const detectedStr = log.detected || "Bilinmiyor";
            if (detectedStr.includes("Kaza") || detectedStr.includes("Kavga") || detectedStr.includes("Kural")) {
                statusBadge = '<span class="badge-row badge-row-anomaly">KRİTİK ANOMALİ</span>';
            } else if (detectedStr.includes("Engel")) {
                statusBadge = '<span class="badge-row badge-row-warning">UYARI</span>';
            } else {
                statusBadge = '<span class="badge-row badge-row-normal">NORMAL</span>';
            }
            
            const scoreNum = typeof log.score === 'number' ? log.score : parseFloat(log.score) || 0;
            
            tr.innerHTML = `
                <td>${log.timestamp || '-'}</td>
                <td>
                    <div class="source-cell" title="${sourceStr}">
                        <i class="fa-solid ${icon}"></i>
                        <span>${sourceStr}</span>
                    </div>
                </td>
                <td style="font-weight: 500;">${detectedStr}</td>
                <td style="font-family: monospace; font-weight: 600;">${scoreNum.toFixed(3)}</td>
                <td>${log.mode || '-'}</td>
                <td>${statusBadge}</td>
            `;
            logsTableBody.appendChild(tr);
        });
    }
    
    function clearLogs() {
        if (confirm("Tüm tespit geçmişini temizlemek istediğinizden emin misiniz?")) {
            detectionLogs = [];
            saveLogs();
            renderLogs();
        }
    }
    
    // Notification system
    function showNotification(message, type = "info") {
        // Check if there is an existing notification container, or create one
        let container = document.getElementById("notificationContainer");
        if (!container) {
            container = document.createElement("div");
            container.id = "notificationContainer";
            container.style.position = "fixed";
            container.style.top = "24px";
            container.style.right = "24px";
            container.style.zIndex = "9999";
            container.style.display = "flex";
            container.style.flexDirection = "column";
            container.style.gap = "10px";
            document.body.appendChild(container);
        }
        
        const notif = document.createElement("div");
        notif.style.background = "rgba(16, 18, 27, 0.9)";
        notif.style.backdropFilter = "blur(12px)";
        notif.style.border = "1px solid var(--glass-border)";
        notif.style.padding = "12px 20px";
        notif.style.borderRadius = "8px";
        notif.style.boxShadow = "0 10px 25px rgba(0,0,0,0.5)";
        notif.style.color = "var(--text-primary)";
        notif.style.fontSize = "0.9rem";
        notif.style.fontWeight = "500";
        notif.style.display = "flex";
        notif.style.alignItems = "center";
        notif.style.gap = "10px";
        notif.style.transform = "translateX(50px)";
        notif.style.opacity = "0";
        notif.style.transition = "all 0.3s cubic-bezier(0.1, 0.8, 0.3, 1)";
        
        let icon = "fa-circle-info";
        let color = "var(--accent-cyan)";
        
        if (type === "success") {
            icon = "fa-circle-check";
            color = "var(--success)";
            notif.style.borderColor = "rgba(16, 185, 129, 0.3)";
        } else if (type === "warning") {
            icon = "fa-triangle-exclamation";
            color = "var(--warning)";
            notif.style.borderColor = "rgba(245, 158, 11, 0.3)";
        } else if (type === "danger") {
            icon = "fa-circle-xmark";
            color = "var(--danger)";
            notif.style.borderColor = "rgba(239, 68, 68, 0.3)";
        }
        
        notif.innerHTML = `
            <i class="fa-solid ${icon}" style="color: ${color}; font-size: 1.1rem;"></i>
            <span>${message}</span>
        `;
        
        container.appendChild(notif);
        
        // Animate in
        setTimeout(() => {
            notif.style.transform = "translateX(0)";
            notif.style.opacity = "1";
        }, 10);
        
        // Auto remove
        setTimeout(() => {
            notif.style.transform = "translateX(50px)";
            notif.style.opacity = "0";
            setTimeout(() => {
                notif.remove();
            }, 300);
        }, 4000);
    }
});
