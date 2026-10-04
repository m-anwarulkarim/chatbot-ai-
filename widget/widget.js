(function () {
    // 1. Detect API Key from script tag
    const scriptTag = document.currentScript || document.querySelector('script[data-api-key]');
    const apiKey = scriptTag ? scriptTag.getAttribute('data-api-key') : null;
    const backendUrl = scriptTag ? (scriptTag.getAttribute('data-backend-url') || 'http://localhost:8000') : 'http://localhost:8000';

    if (!apiKey) {
        console.error("AI Chatbot Widget Error: Missing data-api-key attribute in script tag.");
        return;
    }

    let activeLeadId = sessionStorage.getItem(`ai_lead_id_${apiKey}`) || null;

    // 2. Inject Styles
    const style = document.createElement('style');
    style.innerHTML = `
        #ai-chat-bubble {
            position: fixed;
            bottom: 25px;
            right: 25px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #4F46E5, #7C3AED);
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 10px 25px rgba(79, 70, 229, 0.4);
            z-index: 99999;
            transition: transform 0.3s ease;
        }
        #ai-chat-bubble:hover { transform: scale(1.1); }
        #ai-chat-box {
            position: fixed;
            bottom: 95px;
            right: 25px;
            width: 380px;
            height: 520px;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.15);
            display: none;
            flex-direction: column;
            overflow: hidden;
            z-index: 99999;
            font-family: system-ui, -apple-system, sans-serif;
            border: 1px solid #E5E7EB;
        }
        .ai-chat-header {
            background: linear-gradient(135deg, #4F46E5, #7C3AED);
            color: white;
            padding: 16px;
            font-weight: 600;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .ai-lead-form {
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 16px;
            justify-content: center;
            flex: 1;
            background: #FAFAFA;
        }
        .ai-lead-form h3 { margin: 0; font-size: 18px; color: #1F2937; }
        .ai-lead-form p { margin: 0; font-size: 13px; color: #6B7280; }
        .ai-lead-form input {
            padding: 12px;
            border: 1px solid #D1D5DB;
            border-radius: 8px;
            outline: none;
            font-size: 14px;
        }
        .ai-lead-form button {
            background: #4F46E5;
            color: white;
            border: none;
            padding: 12px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            font-size: 14px;
        }
        .ai-chat-messages {
            flex: 1;
            padding: 16px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .ai-msg {
            max-width: 80%;
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 14px;
            line-height: 1.5;
        }
        .ai-msg.bot { background: #F3F4F6; color: #1F2937; align-self: flex-start; }
        .ai-msg.user { background: #4F46E5; color: white; align-self: flex-end; }
        .ai-chat-input-area {
            padding: 12px;
            border-top: 1px solid #E5E7EB;
            display: flex;
            gap: 8px;
        }
        .ai-chat-input-area input {
            flex: 1;
            border: 1px solid #D1D5DB;
            padding: 10px 14px;
            border-radius: 8px;
            outline: none;
        }
        .ai-chat-input-area button {
            background: #4F46E5;
            color: white;
            border: none;
            padding: 10px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
        }
    `;
    document.head.appendChild(style);

    // 3. Inject DOM Elements
    const bubble = document.createElement('div');
    bubble.id = 'ai-chat-bubble';
    bubble.innerHTML = `<svg width="28" height="28" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path></svg>`;

    const box = document.createElement('div');
    box.id = 'ai-chat-box';
    box.innerHTML = `
        <div class="ai-chat-header">
            <span>AI Customer Support</span>
            <span id="ai-chat-close" style="cursor:pointer;">✕</span>
        </div>
        
        <div class="ai-lead-form" id="ai-lead-form" style="${activeLeadId ? 'display:none;' : 'display:flex;'}">
            <h3>Welcome! 👋</h3>
            <p>Please enter your details to start chatting with our AI Assistant.</p>
            <input type="text" id="ai-lead-name" placeholder="Your Name" required />
            <input type="email" id="ai-lead-email" placeholder="Your Email" required />
            <button id="ai-lead-submit">Start Conversation</button>
        </div>

        <div class="ai-chat-messages" id="ai-msg-container" style="${activeLeadId ? 'display:flex;' : 'display:none;'}">
            <div class="ai-msg bot">Hi! How can I help you today?</div>
        </div>

        <div class="ai-chat-input-area" id="ai-input-area" style="${activeLeadId ? 'display:flex;' : 'display:none;'}">
            <input type="text" id="ai-msg-input" placeholder="Type your message..." />
            <button id="ai-msg-send">Send</button>
        </div>
    `;

    document.body.appendChild(bubble);
    document.body.appendChild(box);

    // 4. Handle UI Toggles
    bubble.addEventListener('click', () => {
        box.style.display = box.style.display === 'flex' ? 'none' : 'flex';
    });
    document.getElementById('ai-chat-close').addEventListener('click', () => {
        box.style.display = 'none';
    });

    // 5. Handle Lead Form Submit
    const leadForm = document.getElementById('ai-lead-form');
    const msgContainer = document.getElementById('ai-msg-container');
    const inputArea = document.getElementById('ai-input-area');
    const leadSubmitBtn = document.getElementById('ai-lead-submit');

    leadSubmitBtn.addEventListener('click', async () => {
        const name = document.getElementById('ai-lead-name').value.trim();
        const email = document.getElementById('ai-lead-email').value.trim();

        if (!name || !email) {
            alert('Please enter both your name and email.');
            return;
        }

        try {
            const res = await fetch(`${backendUrl}/api/leads`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: apiKey, name, email })
            });
            const data = await res.json();
            if (res.ok && data.lead_id) {
                activeLeadId = data.lead_id;
                sessionStorage.setItem(`ai_lead_id_${apiKey}`, activeLeadId);

                // Show Chat UI
                leadForm.style.display = 'none';
                msgContainer.style.display = 'flex';
                inputArea.style.display = 'flex';
            } else {
                alert(data.detail || 'Could not save lead details.');
            }
        } catch (err) {
            alert('Network error. Unable to connect to server.');
        }
    });

    // 6. Handle Chat Message Send & SSE Stream
    const input = document.getElementById('ai-msg-input');
    const sendBtn = document.getElementById('ai-msg-send');

    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        // Append User Message
        const userMsg = document.createElement('div');
        userMsg.className = 'ai-msg user';
        userMsg.textContent = text;
        msgContainer.appendChild(userMsg);

        input.value = '';
        msgContainer.scrollTop = msgContainer.scrollHeight;

        // Placeholder for Bot Streaming Message
        const botMsg = document.createElement('div');
        botMsg.className = 'ai-msg bot';
        botMsg.textContent = '...';
        msgContainer.appendChild(botMsg);
        msgContainer.scrollTop = msgContainer.scrollHeight;

        try {
            const response = await fetch(`${backendUrl}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: apiKey, message: text, lead_id: activeLeadId })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            botMsg.textContent = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                botMsg.textContent += chunk;
                msgContainer.scrollTop = msgContainer.scrollHeight;
            }
        } catch (err) {
            botMsg.textContent = "Sorry, unable to connect to AI server.";
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
})();
