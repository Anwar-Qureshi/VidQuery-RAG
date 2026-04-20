// Global State
let isVideoProcessed = false;
let currentVideoId = null;
let widgetInjected = false;

function getVideoId() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('v');
}

// 1. Core initialization for the HTML framework
function injectHTML() {
  if (widgetInjected) return;
  
  // Create toggle button
  const toggleBtn = document.createElement("button");
  toggleBtn.id = "yt-rag-toggle-btn";
  toggleBtn.innerHTML = "✨";
  document.body.appendChild(toggleBtn);

  // Create widget
  const widget = document.createElement("div");
  widget.id = "yt-rag-widget";
  widget.innerHTML = `
    <div id="yt-rag-header">
      <h3>
        <div id="yt-rag-status-dot"></div>
        VidQuery AI
      </h3>
      <button id="yt-rag-close-btn">×</button>
    </div>
    
    <div id="yt-rag-chat-area"></div>

    <div id="yt-rag-input-area">
      <input type="text" id="yt-rag-input" placeholder="Ask a question..." disabled />
      <button id="yt-rag-submit" disabled>➤</button>
    </div>
  `;
  document.body.appendChild(widget);
  widgetInjected = true;

  // Interaction Logic: Open/Close
  toggleBtn.addEventListener("click", () => widget.classList.add("open"));
  document.getElementById("yt-rag-close-btn").addEventListener("click", () => widget.classList.remove("open"));

  setupInteractions();
}

// Helper: Add generic chat messages dynamically
function addMessage(text, role) {
  const chatArea = document.getElementById("yt-rag-chat-area");
  const msg = document.createElement("div");
  msg.classList.add("yt-rag-message", role);
  msg.innerText = text;
  chatArea.appendChild(msg);
  chatArea.scrollTop = chatArea.scrollHeight; // Auto-scroll to bottom
}

// Resets the chat interface when moving to a new video
function resetWidgetUI() {
  isVideoProcessed = false;
  
  // Show widget components
  document.getElementById('yt-rag-widget').style.display = 'flex';
  document.getElementById('yt-rag-toggle-btn').style.display = 'flex';

  const chatArea = document.getElementById("yt-rag-chat-area");
  chatArea.innerHTML = ''; // Wipe old chat history
  
  // Lock inputs
  document.getElementById("yt-rag-input").disabled = true;
  document.getElementById("yt-rag-input").value = "";
  document.getElementById("yt-rag-submit").disabled = true;
  document.getElementById("yt-rag-status-dot").classList.remove("ready");

  // Re-add Process Button
  const welcomeMsg = document.createElement("div");
  welcomeMsg.classList.add("yt-rag-message", "system");
  welcomeMsg.innerText = "Welcome! Press the button below to allow the AI to ingest this video's transcript.";
  
  const processBtn = document.createElement("button");
  processBtn.id = "yt-rag-process-btn";
  processBtn.innerText = "Process Video with FAISS";
  
  chatArea.appendChild(welcomeMsg);
  chatArea.appendChild(processBtn);

  // Hook up event listener for the NEW process button
  processBtn.addEventListener("click", handleProcessClick);
}

// 2. Main Process Logic
async function handleProcessClick() {
  const processBtn = document.getElementById("yt-rag-process-btn");
  const inputField = document.getElementById("yt-rag-input");
  const submitBtn = document.getElementById("yt-rag-submit");
  const statusDot = document.getElementById("yt-rag-status-dot");

  processBtn.innerText = "Extracting & Vectorizing... ";
  processBtn.disabled = true;

  try {
    // THIS IS THE EXACT CHANGE THAT BYPASSES YOUTUBE'S BOT BLOCKERS
    let extractedText = "";
    try {
        const responseHtml = await fetch(window.location.href);
        const html = await responseHtml.text();
        const match = html.match(/"captionTracks":(\[.*?\])/);
        if (match) {
            const tracks = JSON.parse(match[1]);
            let track = tracks.find(t => t.languageCode.startsWith('en')) || tracks[0];
            const xmlResponse = await fetch(track.baseUrl);
            const xmlText = await xmlResponse.text();
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(xmlText, "text/xml");
            const textNodes = xmlDoc.getElementsByTagName("text");
            for (let i = 0; i < textNodes.length; i++) {
                extractedText += textNodes[i].textContent + " ";
            }
            extractedText = extractedText.replace(/\s+/g, ' ').trim();
        }
    } catch (err) {
        console.warn("Browser extraction failed, falling back to python", err);
    }

    const response = await fetch("http://127.0.0.1:8000/api/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
          video_id: currentVideoId,
          transcript_text: extractedText || null
      })
    });
    
    const data = await response.json();
    if (data.status === "success") {
      isVideoProcessed = true;
      processBtn.style.display = "none";
      statusDot.classList.add("ready");
      addMessage(`✅ ${data.message}`, "system");
      
      inputField.disabled = false;
      submitBtn.disabled = false;
      inputField.focus();
    } else {
      processBtn.innerText = "Error - Try Again";
      processBtn.disabled = false;
      addMessage(`❌ Error: ${JSON.stringify(data)}`, "system");
    }
  } catch (error) {
    processBtn.innerText = "Server Error";
    addMessage(`❌ Make sure your local Python server is running!`, "system");
  }
}

// 3. Main Chat Logic
function setupInteractions() {
  const inputField = document.getElementById("yt-rag-input");
  const submitBtn = document.getElementById("yt-rag-submit");

  async function handleSend() {
    const q = inputField.value.trim();
    if (!q || !isVideoProcessed) return;

    addMessage(q, "user");
    inputField.value = "";
    
    const loadingId = "loading-" + Date.now();
    const chatArea = document.getElementById("yt-rag-chat-area");
    const loadingMsg = document.createElement("div");
    loadingMsg.id = loadingId;
    loadingMsg.classList.add("yt-rag-message", "bot");
    loadingMsg.innerText = "Thinking...";
    chatArea.appendChild(loadingMsg);
    chatArea.scrollTop = chatArea.scrollHeight;

    try {
      const response = await fetch("http://127.0.0.1:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_id: currentVideoId, question: q })
      });
      const data = await response.json();
      
      document.getElementById(loadingId).remove();
      if (data.status === "success") {
        addMessage(data.answer, "bot");
      } else {
        addMessage("⚠️ Failed to generate answer.", "bot");
      }
    } catch (e) {
      document.getElementById(loadingId).remove();
      addMessage("⚠️ Connection error with python backend.", "system");
    }
  }

  submitBtn.addEventListener("click", handleSend);
  inputField.addEventListener("keypress", (e) => {
    if (e.key === "Enter") handleSend();
  });
}

// 4. Handle YouTube Single Page App (SPA) Navigation
document.addEventListener('yt-navigate-finish', () => {
    handleNewVideo();
});

// Since yt-navigate-finish might pass before script runs if hitting refresh, check manually once
handleNewVideo();

function handleNewVideo() {
    const newId = getVideoId();
    // If we're on the homepage, hide the widget entirely
    if (!newId) {
        if (widgetInjected) {
            document.getElementById('yt-rag-widget').style.display = 'none';
            document.getElementById('yt-rag-toggle-btn').style.display = 'none';
        }
        return;
    }
    
    // If it is a new video, build or restart the UI
    if (newId !== currentVideoId) {
        currentVideoId = newId;
        
        if (!widgetInjected) {
            injectHTML(); // Inject empty layout FIRST time
        }
        
        // Always reset the UI state to a blank chat for the new video!
        resetWidgetUI();
    }
}
