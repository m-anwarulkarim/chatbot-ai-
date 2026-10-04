<script>
    import { onMount } from 'svelte';

    // Svelte 5 Runes State
    let botName = $state('');
    let systemPrompt = $state('You are a helpful customer support AI assistant for this website. Answer strictly based on website context.');
    let createdBot = $state(null);
    let activeTab = $state('bot'); // 'bot', 'train', 'leads', 'embed'

    // Knowledge & Training State
    let knowledgeText = $state('');
    let knowledgeStatus = $state('');
    let crawlUrl = $state('');
    let crawlStatus = $state('');
    let isCrawling = $state(false);
    let selectedFile = $state(null);
    let uploadStatus = $state('');
    let isUploading = $state(false);
    let isDragging = $state(false);
    let isSubmitting = $state(false);
    let createBotError = $state('');

    // Analytics State
    let leadsList = $state([]);
    let logsList = $state([]);
    let isFetchingLogs = $state(false);
    let copySuccess = $state(false);

    const BACKEND_URL = 'http://localhost:8000';

    async function handleCreateBot() {
        createBotError = '';
        if (!botName.trim()) {
            createBotError = '⚠️ Please enter a Bot Name / Brand Identifier first!';
            return;
        }
        isSubmitting = true;
        try {
            const res = await fetch(`${BACKEND_URL}/api/bots`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: 'user_enterprise',
                    bot_name: botName.trim(),
                    system_prompt: systemPrompt
                })
            });
            if (!res.ok) {
                const errData = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(errData.detail || 'Server returned status ' + res.status);
            }
            const data = await res.json();
            createdBot = data;
            createBotError = '';
            activeTab = 'train';
        } catch (err) {
            createBotError = '❌ Error creating bot: ' + err.message;
        } finally {
            isSubmitting = false;
        }
    }

    async function handleAddKnowledge() {
        if (!createdBot || !knowledgeText.trim()) return;
        knowledgeStatus = '⚡ Embedding & storing vector chunks into PostgreSQL...';
        try {
            const res = await fetch(`${BACKEND_URL}/api/bots/${createdBot.id}/knowledge`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: knowledgeText })
            });
            const data = await res.json();
            knowledgeStatus = '✅ Text knowledge chunk successfully embedded!';
            knowledgeText = '';
        } catch (err) {
            knowledgeStatus = '❌ Failed to save knowledge: ' + err.message;
        }
    }

    async function handleCrawlWebsite() {
        if (!createdBot || !crawlUrl.trim()) return;
        isCrawling = true;
        crawlStatus = '🌐 Scraping website pages & generating Ollama embeddings...';
        try {
            const res = await fetch(`${BACKEND_URL}/api/bots/${createdBot.id}/crawl`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: crawlUrl })
            });
            const data = await res.json();
            if (res.ok) {
                crawlStatus = `✅ ${data.message}`;
                crawlUrl = '';
            } else {
                crawlStatus = `❌ Error: ${data.detail || 'Crawl failed'}`;
            }
        } catch (err) {
            crawlStatus = '❌ Crawl failed: ' + err.message;
        } finally {
            isCrawling = false;
        }
    }

    function handleFileSelect(e) {
        const files = e.target.files || e.dataTransfer.files;
        if (files && files.length > 0) {
            selectedFile = files[0];
        }
    }

    async function handleUploadDocument() {
        if (!createdBot || !selectedFile) return;
        isUploading = true;
        uploadStatus = '📄 Parsing document text & extracting vector chunks...';
        
        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
            const res = await fetch(`${BACKEND_URL}/api/bots/${createdBot.id}/upload-document`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (res.ok) {
                uploadStatus = `✅ ${data.message}`;
                selectedFile = null;
            } else {
                uploadStatus = `❌ Error: ${data.detail || 'Upload failed'}`;
            }
        } catch (err) {
            uploadStatus = '❌ Upload failed: ' + err.message;
        } finally {
            isUploading = false;
        }
    }

    async function fetchLeadsAndLogs() {
        if (!createdBot) return;
        isFetchingLogs = true;
        try {
            const [leadsRes, logsRes] = await Promise.all([
                fetch(`${BACKEND_URL}/api/bots/${createdBot.id}/leads`),
                fetch(`${BACKEND_URL}/api/bots/${createdBot.id}/logs`)
            ]);
            leadsList = await leadsRes.json();
            logsList = await logsRes.json();
        } catch (err) {
            console.error('Failed to fetch logs:', err);
        } finally {
            isFetchingLogs = false;
        }
    }

    function copyEmbedCode() {
        if (!createdBot) return;
        const code = '<script src="' + BACKEND_URL + '/widget.js" data-api-key="' + createdBot.api_key + '" defer><' + '/script>';
        navigator.clipboard.writeText(code);
        copySuccess = true;
        setTimeout(() => copySuccess = false, 3000);
    }
</script>

<div class="max-w-7xl mx-auto px-4 py-8 space-y-8 font-sans">
    <!-- Header Navbar -->
    <header class="flex flex-col md:flex-row justify-between items-center p-5 bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl shadow-2xl gap-4">
        <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-tr from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center text-xl font-bold text-white shadow-lg shadow-indigo-500/30">
                ⚡
            </div>
            <div>
                <h1 class="text-xl font-extrabold text-white tracking-tight">Antigravity AI SaaS</h1>
                <p class="text-xs text-slate-400">Self-Hosted RAG AI Engine</p>
            </div>
            <span class="ml-2 px-2.5 py-1 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-md text-xs font-semibold">
                Tailwind CSS
            </span>
        </div>

        {#if createdBot}
            <div class="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full text-emerald-400 text-sm font-medium">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>Active Bot: <strong class="text-emerald-300">{createdBot.bot_name}</strong></span>
            </div>
        {/if}
    </header>

    <!-- Hero Title -->
    <div class="text-center space-y-3 max-w-3xl mx-auto">
        <h2 class="text-3xl md:text-5xl font-extrabold bg-gradient-to-r from-white via-slate-200 to-indigo-400 bg-clip-text text-transparent">
            Custom AI Chatbot Platform
        </h2>
        <p class="text-slate-400 text-base md:text-lg">
            Train AI assistants with your website URLs, PDF books, or custom knowledge base using local Ollama & PostgreSQL vector search.
        </p>
    </div>

    <!-- Navigation Tabs -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-2 bg-slate-900/60 p-2 rounded-xl border border-slate-800/80 backdrop-blur-md">
        <button 
            class="px-4 py-3 rounded-lg font-semibold text-sm transition-all duration-200 flex items-center justify-center gap-2 {activeTab === 'bot' ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-600/30' : 'text-slate-400 hover:text-white hover:bg-slate-800/50'}"
            onclick={() => activeTab = 'bot'}
        >
            <span>🤖 1. Bot Setup</span>
        </button>

        <button 
            class="px-4 py-3 rounded-lg font-semibold text-sm transition-all duration-200 flex items-center justify-center gap-2 {!createdBot ? 'opacity-40 cursor-not-allowed text-slate-500' : activeTab === 'train' ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-600/30' : 'text-slate-400 hover:text-white hover:bg-slate-800/50'}"
            disabled={!createdBot}
            onclick={() => activeTab = 'train'}
        >
            <span>📚 2. Data Training</span>
        </button>

        <button 
            class="px-4 py-3 rounded-lg font-semibold text-sm transition-all duration-200 flex items-center justify-center gap-2 {!createdBot ? 'opacity-40 cursor-not-allowed text-slate-500' : activeTab === 'leads' ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-600/30' : 'text-slate-400 hover:text-white hover:bg-slate-800/50'}"
            disabled={!createdBot}
            onclick={() => { activeTab = 'leads'; fetchLeadsAndLogs(); }}
        >
            <span>📊 3. Leads & History</span>
        </button>

        <button 
            class="px-4 py-3 rounded-lg font-semibold text-sm transition-all duration-200 flex items-center justify-center gap-2 {!createdBot ? 'opacity-40 cursor-not-allowed text-slate-500' : activeTab === 'embed' ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-600/30' : 'text-slate-400 hover:text-white hover:bg-slate-800/50'}"
            disabled={!createdBot}
            onclick={() => activeTab = 'embed'}
        >
            <span>⚡ 4. Widget Embed</span>
        </button>
    </div>

    <!-- TAB 1: BOT SETUP -->
    {#if activeTab === 'bot'}
        <div class="bg-slate-900/70 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 md:p-8 shadow-2xl space-y-6">
            <div class="border-b border-slate-800 pb-4">
                <h3 class="text-2xl font-bold text-white flex items-center gap-2">🤖 Create AI Bot Assistant</h3>
                <p class="text-slate-400 text-sm mt-1">Set name and system instructions for your chatbot.</p>
            </div>

            <div class="space-y-5 max-w-2xl">
                <div class="space-y-2">
                    <label for="bot-name" class="block text-sm font-semibold text-slate-300">Bot Name / Brand Identifier</label>
                    <input 
                        id="bot-name" 
                        type="text" 
                        bind:value={botName} 
                        oninput={(e) => { botName = e.target.value; createBotError = ''; }}
                        placeholder="e.g. My E-commerce Support Bot" 
                        class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 outline-none transition-all" 
                    />
                </div>

                <div class="space-y-2">
                    <label for="sys-prompt" class="block text-sm font-semibold text-slate-300">System Instructions (Prompt)</label>
                    <textarea id="sys-prompt" bind:value={systemPrompt} oninput={(e) => systemPrompt = e.target.value} rows="3" class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 outline-none transition-all"></textarea>
                </div>

                {#if createBotError}
                    <div class="p-4 bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded-xl text-sm font-medium flex items-center gap-2">
                        <span>{createBotError}</span>
                    </div>
                {/if}

                <button 
                    type="button"
                    class="px-6 py-3.5 bg-gradient-to-r from-indigo-600 via-purple-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-semibold rounded-xl shadow-lg shadow-indigo-600/30 hover:shadow-indigo-600/50 hover:-translate-y-0.5 transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-wait" 
                    onclick={handleCreateBot} 
                    disabled={isSubmitting}
                >
                    {#if isSubmitting}
                        <span class="inline-flex items-center gap-2">
                            <svg class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Creating AI Bot...
                        </span>
                    {:else}
                        ✨ Create Bot & Generate API Key
                    {/if}
                </button>
            </div>

            {#if createdBot}
                <div class="mt-6 bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-5 space-y-2 text-emerald-300">
                    <div class="font-bold text-base flex items-center gap-2">✅ Bot Created & Ready for Training</div>
                    <div class="text-sm space-y-1 font-mono">
                        <div>Bot ID: <code class="bg-slate-950 text-sky-400 px-2 py-0.5 rounded border border-slate-800">{createdBot.id}</code></div>
                        <div>API Key: <code class="bg-slate-950 text-sky-400 px-2 py-0.5 rounded border border-slate-800">{createdBot.api_key}</code></div>
                    </div>
                </div>
            {/if}
        </div>
    {/if}

    <!-- TAB 2: DATA TRAINING -->
    {#if activeTab === 'train'}
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Method A: Auto Crawler -->
            <div class="bg-slate-900/70 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
                <div>
                    <h3 class="text-xl font-bold text-white flex items-center gap-2">🌐 Website Auto-Crawler</h3>
                    <p class="text-slate-400 text-xs mt-1">Scrape web pages automatically to build vector embeddings.</p>
                </div>

                <div class="flex gap-2">
                    <input type="url" bind:value={crawlUrl} placeholder="https://example.com/about-us" disabled={isCrawling} class="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:border-indigo-500 outline-none text-sm" />
                    <button class="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl text-sm transition-all disabled:opacity-50" onclick={handleCrawlWebsite} disabled={!crawlUrl.trim() || isCrawling}>
                        {isCrawling ? 'Crawling...' : 'Crawl Page'}
                    </button>
                </div>
                {#if crawlStatus}<p class="text-xs text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 p-2.5 rounded-lg">{crawlStatus}</p>{/if}
            </div>

            <!-- Method B: Document Upload -->
            <div class="bg-slate-900/70 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
                <div>
                    <h3 class="text-xl font-bold text-white flex items-center gap-2">📁 Document Upload</h3>
                    <p class="text-slate-400 text-xs mt-1">Upload PDF files, Word (.docx) documents, or Text notes.</p>
                </div>

                <div 
                    class="border-2 border-dashed border-slate-700 hover:border-indigo-500 bg-slate-950/50 hover:bg-indigo-950/20 rounded-xl p-6 text-center cursor-pointer transition-all duration-200"
                    class:border-indigo-500={isDragging}
                    ondragover={(e) => { e.preventDefault(); isDragging = true; }}
                    ondragleave={() => isDragging = false}
                    ondrop={(e) => { e.preventDefault(); isDragging = false; handleFileSelect(e); }}
                >
                    <input type="file" id="file-in" accept=".pdf,.docx,.txt" onchange={handleFileSelect} class="hidden" />
                    <label for="file-in" class="cursor-pointer flex flex-col items-center gap-2 text-slate-400 text-sm">
                        <span class="text-3xl">📄</span>
                        <span>{selectedFile ? selectedFile.name : 'Drag & Drop PDF/DOCX file here or click to browse'}</span>
                    </label>
                </div>

                <button class="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl text-sm transition-all disabled:opacity-50" onclick={handleUploadDocument} disabled={!selectedFile || isUploading}>
                    {isUploading ? 'Parsing & Vectorizing...' : 'Upload & Train AI'}
                </button>
                {#if uploadStatus}<p class="text-xs text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 p-2.5 rounded-lg">{uploadStatus}</p>{/if}
            </div>

            <!-- Method C: Manual Text -->
            <div class="md:col-span-2 bg-slate-900/70 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
                <div>
                    <h3 class="text-xl font-bold text-white flex items-center gap-2">📝 Manual Knowledge Entry</h3>
                    <p class="text-slate-400 text-xs mt-1">Paste custom product lists, shipping rules, or text notes directly.</p>
                </div>
                <textarea bind:value={knowledgeText} rows="3" placeholder="Type or paste custom text knowledge here..." class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:border-indigo-500 outline-none text-sm"></textarea>
                <button class="px-6 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-semibold rounded-xl text-sm hover:from-indigo-500 hover:to-purple-500 transition-all disabled:opacity-50" onclick={handleAddKnowledge} disabled={!knowledgeText.trim()}>
                    Add Knowledge Chunk
                </button>
                {#if knowledgeStatus}<p class="text-xs text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 p-2.5 rounded-lg">{knowledgeStatus}</p>{/if}
            </div>
        </div>
    {/if}

    <!-- TAB 3: LEADS & LOGS -->
    {#if activeTab === 'leads'}
        <div class="bg-slate-900/70 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 md:p-8 shadow-2xl space-y-8">
            <div class="flex justify-between items-center border-b border-slate-800 pb-4">
                <div>
                    <h3 class="text-2xl font-bold text-white">📊 Customer Leads & Chat History</h3>
                    <p class="text-slate-400 text-sm mt-1">Real-time leads captured from widget and conversation logs.</p>
                </div>
                <button class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl text-sm font-semibold transition-all" onclick={fetchLeadsAndLogs} disabled={isFetchingLogs}>
                    {isFetchingLogs ? 'Refreshing...' : '🔄 Refresh Logs'}
                </button>
            </div>

            <!-- Leads Section -->
            <div class="space-y-4">
                <h4 class="text-lg font-bold text-slate-200 flex items-center gap-2">👥 Collected Customer Leads ({leadsList.length})</h4>
                {#if leadsList.length === 0}
                    <p class="text-slate-500 text-sm">No leads collected yet. Pre-chat lead forms will automatically populate customer data here.</p>
                {:else}
                    <div class="overflow-x-auto border border-slate-800 rounded-xl">
                        <table class="w-full text-left text-sm text-slate-300 border-collapse">
                            <thead class="bg-slate-950 text-slate-400 uppercase text-xs tracking-wider border-b border-slate-800">
                                <tr>
                                    <th class="p-3.5">Customer Name</th>
                                    <th class="p-3.5">Email Address</th>
                                    <th class="p-3.5">Timestamp</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-800/60 bg-slate-900/40">
                                {#each leadsList as lead}
                                    <tr class="hover:bg-slate-800/30 transition-all">
                                        <td class="p-3.5 font-semibold text-slate-100">{lead.name}</td>
                                        <td class="p-3.5 text-indigo-300">{lead.email}</td>
                                        <td class="p-3.5 text-slate-400 text-xs">{new Date(lead.created_at).toLocaleString()}</td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </div>
                {/if}
            </div>

            <!-- Conversation Logs -->
            <div class="space-y-4 pt-4 border-t border-slate-800">
                <h4 class="text-lg font-bold text-slate-200 flex items-center gap-2">💬 Conversation History</h4>
                {#if logsList.length === 0}
                    <p class="text-slate-500 text-sm">No conversation logs recorded yet.</p>
                {:else}
                    <div class="space-y-3 max-h-96 overflow-y-auto pr-2">
                        {#each logsList as log}
                            <div class="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 space-y-2 text-sm">
                                <div class="flex justify-between items-center text-xs text-slate-400 border-b border-slate-800/60 pb-2">
                                    <span>👤 <strong class="text-slate-200">{log.lead_name || 'Anonymous Visitor'}</strong> ({log.lead_email || 'N/A'})</span>
                                    <span>{new Date(log.created_at).toLocaleString()}</span>
                                </div>
                                <div class="text-slate-300"><strong>User:</strong> {log.user_message}</div>
                                <div class="text-indigo-300"><strong>AI Bot:</strong> {log.bot_response}</div>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        </div>
    {/if}

    <!-- TAB 4: EMBED -->
    {#if activeTab === 'embed'}
        <div class="bg-slate-900/70 backdrop-blur-xl border border-slate-800 rounded-2xl p-6 md:p-8 shadow-2xl space-y-6">
            <div class="border-b border-slate-800 pb-4">
                <h3 class="text-2xl font-bold text-white flex items-center gap-2">⚡ Embed Widget Snippet</h3>
                <p class="text-slate-400 text-sm mt-1">Copy and paste this script tag into the HTML head or body of any website.</p>
            </div>

            <div class="bg-slate-950 border border-slate-800 rounded-xl p-5 font-mono text-sm text-sky-400 overflow-x-auto shadow-inner">
                <pre><code>&lt;script 
  src="{BACKEND_URL}/widget.js" 
  data-api-key="{createdBot.api_key}" 
  defer&gt;
&lt;/script&gt;</code></pre>
            </div>

            <button class="px-6 py-3.5 bg-gradient-to-r from-indigo-600 via-purple-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-semibold rounded-xl shadow-lg shadow-indigo-600/30 transition-all" onclick={copyEmbedCode}>
                {copySuccess ? '✅ Copied to Clipboard!' : '📋 Copy Embed Script'}
            </button>
        </div>
    {/if}
</div>
