// Veritas Client-side Dashboard Controller

let spreadChart = null;
let analysisHistory = JSON.parse(localStorage.getItem('veritas_history')) || [];

const LOADING_STEPS = [
    "Scraping social media indices...",
    "Querying Google FactCheck database...",
    "Scraping live search pages...",
    "Analyzing domain distributions...",
    "Invoking Gemini reasoning models...",
    "Compiling truth report..."
];

// Document initialization
document.addEventListener("DOMContentLoaded", () => {
    generateBackgroundSparkles();
    checkApiStatus();
    renderHistory();
    initChart();
    
    const form = document.getElementById("analyze-form");
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const query = document.getElementById("query-input").value.trim();
        if (query) {
            triggerAnalysis(query);
        }
    });
});

// Sparkles Background Generator
function generateBackgroundSparkles() {
    const container = document.getElementById("sparkles");
    if (!container) return;
    
    const count = 40;
    for (let i = 0; i < count; i++) {
        const sparkle = document.createElement("div");
        sparkle.className = "sparkle";
        sparkle.style.top = `${Math.random() * 100}%`;
        sparkle.style.left = `${Math.random() * 100}%`;
        sparkle.style.animationDelay = `${Math.random() * 4}s`;
        sparkle.style.transform = `scale(${Math.random() * 1.6 + 0.4})`;
        container.appendChild(sparkle);
    }
}

// Chart.js Setup
function initChart() {
    const ctx = document.getElementById('spread-chart').getContext('2d');
    if (!ctx) return;
    
    Chart.defaults.color = '#a1a1aa';
    Chart.defaults.font.family = "'Outfit', sans-serif";
    
    spreadChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['X / Twitter', 'Reddit', 'Facebook', 'YouTube', 'TikTok', 'Instagram'],
            datasets: [{
                label: 'Viral Index',
                data: [0, 0, 0, 0, 0, 0],
                backgroundColor: function(context) {
                    const chart = context.chart;
                    const {ctx, chartArea} = chart;
                    if (!chartArea) return null;
                    
                    const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
                    gradient.addColorStop(0, '#8b5cf6'); // Violet
                    gradient.addColorStop(1, '#06b6d4'); // Teal
                    return gradient;
                },
                borderRadius: 8,
                borderWidth: 0,
                barThickness: 20,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#0f0f15',
                    titleColor: '#ffffff',
                    bodyColor: '#e4e4e7',
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1,
                    padding: 10,
                    displayColors: false,
                    callbacks: {
                        label: function(context) {
                            return `Spread Index: ${context.parsed.y}%`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.04)', drawTicks: false },
                    border: { dash: [4, 4] },
                    ticks: { callback: value => `${value}%` },
                    min: 0,
                    max: 100
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}

// Check backend mode status badge
async function checkApiStatus() {
    const textEl = document.getElementById("api-mode-text");
    const badgeEl = document.getElementById("api-status-badge");
    if (!textEl || !badgeEl) return;
    
    const pulseDot = badgeEl.querySelector(".pulse-dot");
    
    try {
        const res = await fetch("/api/status");
        if (res.ok) {
            const status = await res.json();
            if (status.mode === "Live") {
                textEl.innerText = "Live AI Mode Active";
                textEl.style.color = "#10b981";
                pulseDot.style.backgroundColor = "#10b981";
                pulseDot.style.boxShadow = "0 0 10px #10b981";
            } else {
                textEl.innerText = "Demo Mode (Mock Data)";
                textEl.style.color = "#f59e0b";
                pulseDot.style.backgroundColor = "#f59e0b";
                pulseDot.style.boxShadow = "0 0 10px #f59e0b";
            }
        } else {
            throw new Error();
        }
    } catch (e) {
        textEl.innerText = "Offline";
        textEl.style.color = "#ef4444";
        pulseDot.style.backgroundColor = "#ef4444";
        pulseDot.style.boxShadow = "0 0 10px #ef4444";
    }
}

// Controller State Switching
function switchState(stateName) {
    document.querySelectorAll(".state-container").forEach(el => {
        el.classList.remove("active");
    });
    const stateEl = document.getElementById(`state-${stateName}`);
    if (stateEl) {
        stateEl.classList.add("active");
    }
}

function resetToIdle() {
    switchState("idle");
    document.getElementById("query-input").value = "";
}

// Perform Analysis Fetch
async function triggerAnalysis(query) {
    switchState("loading");
    
    const typingText = document.querySelector(".typing-text");
    const subtext = document.getElementById("loading-subtext");
    const progressFill = document.getElementById("progress-fill");
    const submitBtn = document.getElementById("submit-btn");
    
    submitBtn.disabled = true;
    progressFill.style.width = "10%";
    
    let loadStep = 0;
    const interval = setInterval(() => {
        loadStep++;
        if (loadStep < LOADING_STEPS.length) {
            typingText.innerText = LOADING_STEPS[loadStep];
            subtext.innerText = `Resolving verification pipelines (step ${loadStep + 1} of 6)...`;
            progressFill.style.width = `${10 + loadStep * 15}%`;
        }
    }, 1100);
    
    try {
        const res = await fetch(`/api/analyze?q=${encodeURIComponent(query)}`);
        clearInterval(interval);
        
        if (!res.ok) {
            throw new Error(`Server API status error: ${res.statusText}`);
        }
        
        const result = await res.json();
        progressFill.style.width = "100%";
        
        setTimeout(() => {
            renderResults(result);
            saveHistory(result);
            submitBtn.disabled = false;
        }, 500);
        
    } catch (e) {
        clearInterval(interval);
        console.error(e);
        document.getElementById("error-message").innerText = `Failed to complete analysis. Details: ${e.message || "Connection refused"}`;
        switchState("error");
        submitBtn.disabled = false;
    }
}

// Render API payload values to DOM
function renderResults(result) {
    switchState("success");
    
    // Echo Query
    document.getElementById("result-query").innerText = result.query;
    
    // Verdict Styling
    const verdictEl = document.getElementById("result-verdict");
    verdictEl.innerText = result.verdict;
    verdictEl.className = `verdict-text verdict-${result.verdict}`;
    
    const verdictCard = document.querySelector(".verdict-card");
    verdictCard.className = `verdict-card glass-card span-all-cols verdict-${result.verdict}`;
    
    // Trust Score Gauge Circle
    const scoreVal = document.getElementById("result-score");
    scoreVal.innerText = result.trust_score;
    
    const meter = document.getElementById("score-meter");
    const radius = meter.r.baseVal.value;
    const circumference = 2 * Math.PI * radius;
    const strokeOffset = circumference - (result.trust_score / 100) * circumference;
    
    // Colors variables mapping
    let colorHex = "#3b82f6"; // Blue (Unverified)
    if (result.verdict === "TRUE") colorHex = "#10b981"; // Green
    if (result.verdict === "FALSE") colorHex = "#ef4444"; // Red
    if (result.verdict === "MISLEADING") colorHex = "#f59e0b"; // Amber
    
    meter.style.stroke = colorHex;
    meter.style.strokeDashoffset = strokeOffset;
    
    // Platform Spread Velocity Badge
    const velocityBadge = document.getElementById("result-velocity");
    const velocityText = document.getElementById("result-velocity-text");
    velocityText.innerText = `${result.spread_velocity.toUpperCase()} VELOCITY`;
    
    velocityBadge.className = "velocity-badge";
    if (result.spread_velocity.toLowerCase() === "critical") {
        velocityBadge.style.color = "var(--false-color)";
        velocityBadge.style.borderColor = "var(--false-glow)";
        velocityBadge.style.background = "rgba(239, 68, 68, 0.05)";
    } else if (result.spread_velocity.toLowerCase() === "high") {
        velocityBadge.style.color = "var(--misleading-color)";
        velocityBadge.style.borderColor = "var(--misleading-glow)";
        velocityBadge.style.background = "rgba(245, 158, 11, 0.05)";
    } else {
        velocityBadge.style.color = "var(--true-color)";
        velocityBadge.style.borderColor = "var(--true-glow)";
        velocityBadge.style.background = "rgba(16, 185, 129, 0.05)";
    }
    
    // Update Chart values
    const spreadLabels = Object.keys(result.platform_spread);
    const spreadVals = Object.values(result.platform_spread);
    
    spreadChart.data.labels = spreadLabels;
    spreadChart.data.datasets[0].data = spreadVals;
    spreadChart.update();
    
    // AI Explanation markdown parsing
    document.getElementById("result-explanation").innerHTML = formatReportText(result.explanation);
    
    // Metadata footer
    document.getElementById("result-timestamp").innerText = `Analysis Timestamp: ${result.timestamp}`;
    
    // Render Grounding citations
    const sourcesGrid = document.getElementById("result-sources");
    sourcesGrid.innerHTML = "";
    
    if (result.sources && result.sources.length > 0) {
        result.sources.forEach(src => {
            const card = document.createElement("a");
            card.href = src.url;
            card.target = "_blank";
            card.className = "source-item";
            
            // Format rating text colors
            let styleAttr = "color: var(--text-secondary);";
            const ratingLow = src.rating.toLowerCase();
            if (ratingLow.includes("false") || ratingLow.includes("fake") || ratingLow.includes("debunked")) {
                styleAttr = "color: var(--false-color);";
            } else if (ratingLow.includes("true") || ratingLow.includes("verified") || ratingLow.includes("fact")) {
                styleAttr = "color: var(--true-color);";
            } else if (ratingLow.includes("misleading") || ratingLow.includes("context")) {
                styleAttr = "color: var(--misleading-color);";
            }
            
            card.innerHTML = `
                <div class="source-header">
                    <span class="source-publisher"><i class="fa-solid fa-arrow-up-right-from-square"></i> ${src.publisher}</span>
                    <span class="source-rating" style="${styleAttr}">${src.rating}</span>
                </div>
                <div class="source-title" title="${src.title}">${src.title}</div>
            `;
            sourcesGrid.appendChild(card);
        });
    } else {
        sourcesGrid.innerHTML = `<div class="empty-history span-all-cols" style="padding: 1.5rem 0;">No fact check citations found. Real-time search query results did not return standard articles.</div>`;
    }
}

// Convert mock paragraphs and bold markdown tags
function formatReportText(text) {
    if (!text) return "";
    
    let parsed = text.split("\n\n").map(para => `<p>${para}</p>`).join("");
    parsed = parsed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    return parsed;
}

// Save history caches
function saveHistory(result) {
    analysisHistory = analysisHistory.filter(item => item.query.toLowerCase() !== result.query.toLowerCase());
    
    analysisHistory.unshift({
        query: result.query,
        verdict: result.verdict,
        timestamp: result.timestamp,
        data: result
    });
    
    // Restrict list to 8 items
    if (analysisHistory.length > 8) {
        analysisHistory.pop();
    }
    
    localStorage.setItem('veritas_history', JSON.stringify(analysisHistory));
    renderHistory();
}

function renderHistory() {
    const list = document.getElementById("history-list");
    if (!list) return;
    
    list.innerHTML = "";
    
    if (analysisHistory.length === 0) {
        list.innerHTML = `<li class="empty-history">No recent searches</li>`;
        return;
    }
    
    analysisHistory.forEach(item => {
        const li = document.createElement("li");
        li.className = `history-item verdict-${item.verdict}`;
        li.innerHTML = `
            <span class="claim-text" title="${item.query}">${item.query}</span>
            <span class="verdict-tag">${item.verdict}</span>
        `;
        
        li.addEventListener("click", () => {
            document.getElementById("query-input").value = item.query;
            renderResults(item.data);
        });
        
        list.appendChild(li);
    });
}
