// App State Variables
let spreadChart = null;
let analysisHistory = JSON.parse(localStorage.getItem('veritas_history')) || [];

// Constants
const LOADING_MESSAGES = [
    "Scraping social media index feeds...",
    "Querying Google FactCheck API...",
    "Running real-time domain frequency searches...",
    "Aggregating platform metrics...",
    "Running Gemini LLM reasoning...",
    "Finalizing fact-checking reports..."
];

// Document Ready
document.addEventListener("DOMContentLoaded", () => {
    generateBackgroundSparkles();
    checkApiStatus();
    renderHistory();
    initChart();
    
    // Form submission handler
    const form = document.getElementById("analyze-form");
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const input = document.getElementById("query-input").value.trim();
        if (input) {
            triggerAnalysis(input);
        }
    });
});

// Generate dynamic background particles
function generateBackgroundSparkles() {
    const container = document.getElementById("sparkles");
    const count = 35;
    for (let i = 0; i < count; i++) {
        const sparkle = document.createElement("div");
        sparkle.className = "sparkle";
        sparkle.style.top = `${Math.random() * 100}%`;
        sparkle.style.left = `${Math.random() * 100}%`;
        sparkle.style.animationDelay = `${Math.random() * 4}s`;
        sparkle.style.transform = `scale(${Math.random() * 1.5 + 0.5})`;
        container.appendChild(sparkle);
    }
}

// Initialise Chart.js
function initChart() {
    const ctx = document.getElementById('spread-chart').getContext('2d');
    
    Chart.defaults.color = '#a1a1aa';
    Chart.defaults.font.family = "'Outfit', sans-serif";
    
    spreadChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Twitter/X', 'Reddit', 'Facebook', 'YouTube', 'TikTok', 'Instagram'],
            datasets: [{
                label: 'Viral Index',
                data: [0, 0, 0, 0, 0, 0],
                backgroundColor: function(context) {
                    const chart = context.chart;
                    const {ctx, chartArea} = chart;
                    if (!chartArea) return null;
                    
                    // Dynamic vertical gradient for bars
                    const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
                    gradient.addColorStop(0, '#8b5cf6'); // Violet
                    gradient.addColorStop(1, '#06b6d4'); // Teal
                    return gradient;
                },
                borderRadius: 8,
                borderWidth: 0,
                barThickness: 24,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#18181b',
                    titleColor: '#ffffff',
                    bodyColor: '#e4e4e7',
                    borderColor: '#27272a',
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
                    grid: { color: 'rgba(255, 255, 255, 0.05)', drawTicks: false },
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

// Check Backend API Connection Status
async function checkApiStatus() {
    const statusText = document.getElementById("api-mode-text");
    const statusBadge = document.getElementById("api-status-badge");
    const pulseDot = statusBadge.querySelector(".pulse-dot");
    
    try {
        const response = await fetch("/api/status");
        if (response.ok) {
            const data = await response.json();
            if (data.mode === "Live") {
                statusText.innerText = "Live AI Mode Active";
                statusText.style.color = "#10b981";
                pulseDot.style.backgroundColor = "#10b981";
                pulseDot.style.boxShadow = "0 0 10px #10b981";
            } else {
                statusText.innerText = "Demo Mode (Mock Data)";
                statusText.style.color = "#f59e0b";
                pulseDot.style.backgroundColor = "#f59e0b";
                pulseDot.style.boxShadow = "0 0 10px #f59e0b";
            }
        } else {
            throw new Error();
        }
    } catch (e) {
        statusText.innerText = "Offline";
        statusText.style.color = "#ef4444";
        pulseDot.style.backgroundColor = "#ef4444";
        pulseDot.style.boxShadow = "0 0 10px #ef4444";
    }
}

// Switch UI active view states
function switchState(stateName) {
    document.querySelectorAll(".state-container").forEach(el => {
        el.classList.remove("active");
    });
    document.getElementById(`state-${stateName}`).classList.add("active");
}

function resetToIdle() {
    switchState("idle");
    document.getElementById("query-input").value = "";
}

// Perform Claim Analysis fetch
async function triggerAnalysis(query) {
    switchState("loading");
    
    // Animate loader texts and progress bar sequentially
    const textEl = document.querySelector(".typing-text");
    const subtextEl = document.getElementById("loading-subtext");
    const progressFill = document.getElementById("progress-fill");
    const submitBtn = document.getElementById("submit-btn");
    
    submitBtn.disabled = true;
    progressFill.style.width = "10%";
    
    let step = 0;
    const msgInterval = setInterval(() => {
        step++;
        if (step < LOADING_MESSAGES.length) {
            textEl.innerText = LOADING_MESSAGES[step];
            subtextEl.innerText = `Performing network queries (step ${step + 1} of 6)...`;
            progressFill.style.width = `${10 + step * 15}%`;
        }
    }, 1200);
    
    try {
        const response = await fetch(`/api/analyze?q=${encodeURIComponent(query)}`);
        clearInterval(msgInterval);
        
        if (!response.ok) {
            throw new Error(`Server returned error: ${response.statusText}`);
        }
        
        const result = await response.json();
        progressFill.style.width = "100%";
        
        // Wait slightly for visual flow, then show results
        setTimeout(() => {
            renderResults(result);
            saveToHistory(result);
            submitBtn.disabled = false;
        }, 500);
        
    } catch (err) {
        clearInterval(msgInterval);
        console.error(err);
        document.getElementById("error-message").innerText = `Failed to process claim. Details: ${err.message || "Connection refused"}`;
        switchState("error");
        submitBtn.disabled = false;
    }
}

// Render Results to HTML Elements
function renderResults(result) {
    switchState("success");
    
    // 1. Setup Query display
    document.getElementById("result-query").innerText = result.query;
    
    // 2. Setup Verdict Header styling
    const verdictEl = document.getElementById("result-verdict");
    verdictEl.innerText = result.verdict;
    verdictEl.className = `verdict-text verdict-${result.verdict}`;
    
    // 3. Setup Trust Score Meter and text
    const scoreValEl = document.getElementById("result-score");
    scoreValEl.innerText = result.trust_score;
    
    // Animate trust circle
    const meterCircle = document.getElementById("score-meter");
    const radius = meterCircle.r.baseVal.value;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (result.trust_score / 100) * circumference;
    
    // Apply stroke color depending on rating category
    let colorVar = "var(--unverified-color)";
    if (result.verdict === "TRUE") colorVar = "var(--true-color)";
    if (result.verdict === "FALSE") colorVar = "var(--false-color)";
    if (result.verdict === "MISLEADING") colorVar = "var(--misleading-color)";
    
    meterCircle.style.stroke = colorVar;
    meterCircle.style.strokeDashoffset = offset;
    
    // 4. Spread Velocity Badge
    const velocityEl = document.getElementById("result-velocity");
    const velocityText = document.getElementById("result-velocity-text");
    velocityText.innerText = `${result.spread_velocity} SPREAD VELOCITY`;
    
    // Update velocity color code classes
    velocityEl.className = "velocity-badge";
    if (result.spread_velocity === "Critical") {
        velocityEl.style.color = "var(--false-color)";
        velocityEl.style.borderColor = "var(--false-glow)";
        velocityEl.style.background = "rgba(239, 68, 68, 0.05)";
    } else if (result.spread_velocity === "High") {
        velocityEl.style.color = "var(--misleading-color)";
        velocityEl.style.borderColor = "var(--misleading-glow)";
        velocityEl.style.background = "rgba(245, 158, 11, 0.05)";
    } else {
        velocityEl.style.color = "var(--true-color)";
        velocityEl.style.borderColor = "var(--true-glow)";
        velocityEl.style.background = "rgba(16, 185, 129, 0.05)";
    }

    // 5. Update Chart.js values
    const chartLabels = Object.keys(result.platform_spread);
    const chartData = Object.values(result.platform_spread);
    
    spreadChart.data.labels = chartLabels;
    spreadChart.data.datasets[0].data = chartData;
    spreadChart.update();
    
    // 6. Renders AI explanation
    document.getElementById("result-explanation").innerHTML = formatExplanation(result.explanation);
    
    // 7. Update bottom meta tag info
    document.getElementById("result-timestamp").innerText = `Checked at: ${result.timestamp}`;
    
    // 8. Renders Sources Cards
    const sourcesContainer = document.getElementById("result-sources");
    sourcesContainer.innerHTML = "";
    
    if (result.sources && result.sources.length > 0) {
        result.sources.forEach(src => {
            const card = document.createElement("a");
            card.href = src.url;
            card.target = "_blank";
            card.className = "source-item";
            
            // Format rating text color
            let ratingClass = "";
            const ratingLower = src.rating.toLowerCase();
            if (ratingLower.includes("false") || ratingLower.includes("fake") || ratingLower.includes("debunked")) {
                ratingClass = "color: var(--false-color);";
            } else if (ratingLower.includes("true") || ratingLower.includes("verified") || ratingLower.includes("fact")) {
                ratingClass = "color: var(--true-color);";
            } else if (ratingLower.includes("misleading") || ratingLower.includes("context")) {
                ratingClass = "color: var(--misleading-color);";
            }
            
            card.innerHTML = `
                <div class="source-header">
                    <span class="source-publisher"><i class="fa-solid fa-arrow-up-right-from-square"></i> ${src.publisher}</span>
                    <span class="source-rating" style="${ratingClass}">${src.rating}</span>
                </div>
                <div class="source-title" title="${src.title}">${src.title}</div>
            `;
            sourcesContainer.appendChild(card);
        });
    } else {
        sourcesContainer.innerHTML = `<div class="empty-history span-all-cols" style="padding: 1.5rem 0;">No citation links found. Fact check matches have not been indexed yet.</div>`;
    }
}

// Convert markdown-style paragraph into HTML tags (like bold and paragraphs)
function formatExplanation(text) {
    if (!text) return "";
    
    // Replace double newlines with paragraph tags
    let formatted = text.split("\n\n").map(para => `<p>${para}</p>`).join("");
    
    // Replace **text** markdown with bold tags
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    return formatted;
}

// History caching and LocalStorage persistence
function saveToHistory(result) {
    // Remove if already exists to float it to top
    analysisHistory = analysisHistory.filter(item => item.query.toLowerCase() !== result.query.toLowerCase());
    
    // Prepend new item
    analysisHistory.unshift({
        query: result.query,
        verdict: result.verdict,
        timestamp: result.timestamp,
        data: result
    });
    
    // Limit history length to 10 entries
    if (analysisHistory.length > 10) {
        analysisHistory.pop();
    }
    
    localStorage.setItem('veritas_history', JSON.stringify(analysisHistory));
    renderHistory();
}

function renderHistory() {
    const list = document.getElementById("history-list");
    list.innerHTML = "";
    
    if (analysisHistory.length === 0) {
        list.innerHTML = `<li class="empty-history">No recent searches</li>`;
        return;
    }
    
    analysisHistory.forEach((item, index) => {
        const li = document.createElement("li");
        li.className = "history-item";
        li.innerHTML = `
            <span class="claim-text" title="${item.query}">${item.query}</span>
            <span class="verdict-pill verdict-${item.verdict}" style="background: rgba(255,255,255,0.05); padding: 2px 8px; border-radius:12px;">${item.verdict}</span>
        `;
        
        // Re-inject stored data without calling API again (instant loading)
        li.addEventListener("click", () => {
            document.getElementById("query-input").value = item.query;
            renderResults(item.data);
        });
        
        list.appendChild(li);
    });
}
