// Main application JavaScript for Python Tutor Frontend

// Configuration - Use relative paths since we're served from the same server
const API_BASE_URL = '';

// Global variables
let editor = null;
let chatMessages = [];
let isProcessing = false;
let typingIndicatorElement = null;
const DEFAULT_CODE = `print("Hello, world!")`;

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    initializeMonacoEditor();
    setupChatInterface();
    setupCodeEditor();
    setupComputerAnimation();
});

// ============================================
// MONACO EDITOR SETUP
// ============================================
function initializeMonacoEditor() {
    require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' } });
    
    require(['vs/editor/editor.main'], () => {
        editor = monaco.editor.create(document.getElementById('editorContainer'), {
            value: DEFAULT_CODE,
            language: 'python',
            theme: 'vs-dark',
            automaticLayout: true,
            fontSize: 14,
            minimap: { enabled: true },
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            lineNumbers: 'on',
            roundedSelection: false,
            cursorStyle: 'line',
            formatOnPaste: true,
            formatOnType: true,
        });
    });
}

// ============================================
// CHAT INTERFACE
// ============================================
function setupChatInterface() {
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');
    
    // Send message on button click
    sendButton.addEventListener('click', sendChatMessage);
    
    // Send message on Enter key
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
}

async function sendChatMessage() {
    const chatInput = document.getElementById('chatInput');
    const question = chatInput.value.trim();
    
    if (!question || isProcessing) {
        return;
    }
    
    // Add user message to chat
    addChatMessage('user', question);
    
    // Clear input
    chatInput.value = '';
    
    // Show typing indicator
    isProcessing = true;
    showTypingIndicator(true);
    
    try {
        // Send request to backend
        const response = await fetch(`${API_BASE_URL}/ask_tutor`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question: question }),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        showTypingIndicator(false);

        // Check for error response
        if (data.error) {
            addChatMessage('ai', `Sorry, I encountered an error: ${data.error}`);
        } else {
            // Add AI response to chat
            addChatMessage('ai', data.answer);
        }
    } catch (error) {
        console.error('Error sending message:', error);
        showTypingIndicator(false);
        addChatMessage('ai', `Sorry, I couldn't connect to the server. Please make sure the backend is running.`);
    } finally {
        isProcessing = false;
        showTypingIndicator(false);
    }
}

function addChatMessage(sender, message) {
    const chatMessagesContainer = document.getElementById('chatMessages');
    
    // Create message bubble
    const messageDiv = document.createElement('div');
    messageDiv.className = `message-bubble flex ${sender === 'user' ? 'justify-end' : 'justify-start'} relative z-10`;
    
    // Dark blue-gray bubble with purple border for all messages (matching image)
    const bubbleClass = 'chat-bubble';
    
    // Format message with code highlighting
    const formattedMessage = formatMessageWithCode(message);
    
    messageDiv.innerHTML = `
        <div class="${bubbleClass}">
            <div class="chat-text">${formattedMessage}</div>
        </div>
    `;
    
    chatMessagesContainer.appendChild(messageDiv);
    
    // Auto-scroll to bottom
    chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    
    // Store message
    chatMessages.push({ sender, message });
}

// Format message text with code block and inline code highlighting
function formatMessageWithCode(text) {
    if (!text) return '';
    
    // Find all code blocks first
    const codeBlockRegex = /```(\w+)?\n?([\s\S]*?)```/g;
    let match;
    const codeBlocks = [];
    
    while ((match = codeBlockRegex.exec(text)) !== null) {
        codeBlocks.push({
            start: match.index,
            end: match.index + match[0].length,
            language: match[1] || 'python',
            code: match[2]
        });
    }
    
    // Process text with code blocks
    let formatted = '';
    let currentIndex = 0;
    
    codeBlocks.forEach((block, index) => {
        // Add text before code block
        if (block.start > currentIndex) {
            const textBefore = text.substring(currentIndex, block.start);
            formatted += formatRegularText(textBefore);
        }
        
        // Add formatted code block
        const escapedCode = escapeHtml(block.code.trim());
        formatted += `<pre class="code-block"><code class="language-${block.language}">${escapedCode}</code></pre>`;
        
        currentIndex = block.end;
    });
    
    // Add remaining text after last code block
    if (currentIndex < text.length) {
        formatted += formatRegularText(text.substring(currentIndex));
    }
    
    // If no code blocks found, format entire text as regular
    if (codeBlocks.length === 0) {
        formatted = formatRegularText(text);
    }
    
    return formatted;
}

// Format regular text with inline code and line breaks
function formatRegularText(text) {
    if (!text) return '';
    
    // First handle inline code (but not inside code blocks)
    let formatted = text.replace(/`([^`\n]+)`/g, (match, code) => {
        const escapedCode = escapeHtml(code);
        return `<code class="inline-code">${escapedCode}</code>`;
    });
    
    // Convert line breaks to <br> tags
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
}

// ============================================
// CODE EDITOR & EXECUTION
// ============================================
function setupCodeEditor() {
    const runButton = document.getElementById('runButton');
    const resetButton = document.getElementById('resetButton');
    
    runButton.addEventListener('click', runCode);
    resetButton.addEventListener('click', resetEditor);
}

function resetEditor() {
    if (editor) {
        editor.setValue(DEFAULT_CODE);
        clearConsole();
    }
}

async function runCode() {
    if (!editor || isProcessing) {
        return;
    }
    
    const sourceCode = editor.getValue();
    
    if (!sourceCode.trim()) {
        updateTerminal('info', 'Please write some code before running.');
        return;
    }
    
    // Lock interactions while running
    isProcessing = true;
    updateTerminal('info', 'Running your code...');
    
    try {
        // Send request to backend
        const response = await fetch(`${API_BASE_URL}/run_code`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ source_code: sourceCode }),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Clear previous output
        clearConsole();
        
        // Display status
        const statusClass = data.status === 'Accepted' 
            ? 'status-accepted' 
            : data.status === 'Time Limit Exceeded'
            ? 'status-timeout'
            : 'status-error';
        
        // Display status
        if (data.status) {
            const statusDiv = document.createElement('div');
            statusDiv.className = `console-line mb-2`;
            statusDiv.innerHTML = `<span class="status-badge ${statusClass}">${data.status}</span>`;
            document.getElementById('consoleOutput').appendChild(statusDiv);
        }
        
        // Display stdout
        if (data.stdout) {
            updateTerminal('stdout', data.stdout);
        }
        
        // Display stderr
        if (data.stderr) {
            updateTerminal('stderr', data.stderr);
        }
        
        // Display AI fix if available
        if (data.ai_fix) {
            addAIFix(data.ai_fix);
        }
        
        // If no output, show waiting message
        if (!data.stdout && !data.stderr && data.status === 'Accepted') {
            updateTerminal('info', 'Code executed successfully (no output).');
        }
        
    } catch (error) {
        console.error('Error running code:', error);
        clearConsole();
        updateTerminal('error', `Error: Could not connect to the server. Please make sure the backend is running.`);
    } finally {
        isProcessing = false;
    }
}

function updateTerminal(type, text) {
    const consoleOutput = document.getElementById('consoleOutput');
    
    // Remove the "Waiting for code execution..." message if it exists
    const waitingMsg = consoleOutput.querySelector('.text-green-400');
    if (waitingMsg && waitingMsg.textContent.includes('Waiting')) {
        consoleOutput.innerHTML = '';
    }
    
    const lines = text.split('\n');
    lines.forEach(line => {
        if (line.trim() || lines.length === 1) {
            const lineDiv = document.createElement('div');
            lineDiv.className = `console-line console-${type}`;
            
            // Add terminal prompt style for stdout
            if (type === 'stdout') {
                lineDiv.innerHTML = `<span class="terminal-prompt">~</span> ${escapeHtml(line)}`;
            } else {
                lineDiv.textContent = line;
            }
            
            consoleOutput.appendChild(lineDiv);
        }
    });
    
    // Add blinking cursor
    const cursor = consoleOutput.querySelector('.blink-cursor');
    if (!cursor) {
        const cursorDiv = document.createElement('span');
        cursorDiv.className = 'blink-cursor ml-1';
        cursorDiv.textContent = '|';
        consoleOutput.appendChild(cursorDiv);
    }
    
    // Auto-scroll to bottom
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

function addAIFix(aiFixText) {
    const consoleOutput = document.getElementById('consoleOutput');
    
    const fixContainer = document.createElement('div');
    fixContainer.className = 'ai-fix-container mt-4';
    fixContainer.innerHTML = `
        <h4>🤖 AI Suggestion:</h4>
        <div class="whitespace-pre-wrap">${escapeHtml(aiFixText)}</div>
    `;
    
    consoleOutput.appendChild(fixContainer);
    
    // Auto-scroll to bottom
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

function clearConsole() {
    const consoleOutput = document.getElementById('consoleOutput');
    consoleOutput.innerHTML = `
        <div class="flex items-center gap-2 text-green-400">
            <span class="text-green-500">~</span>
            <span>Waiting for code execution...</span>
            <span class="blink-cursor">|</span>
        </div>
    `;
}

// ============================================
// UTILITY FUNCTIONS
// ============================================
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showTypingIndicator(show) {
    const chatMessagesContainer = document.getElementById('chatMessages');
    
    if (show) {
        if (typingIndicatorElement) {
            return;
        }
        
        typingIndicatorElement = document.createElement('div');
        typingIndicatorElement.className = 'message-bubble flex justify-start relative z-10';
        typingIndicatorElement.innerHTML = `
            <div class="chat-bubble typing-indicator-bubble">
                <div class="typing-dots">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                </div>
            </div>
        `;
        
        chatMessagesContainer.appendChild(typingIndicatorElement);
        chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    } else if (typingIndicatorElement) {
        typingIndicatorElement.remove();
        typingIndicatorElement = null;
    }
}

// ============================================
// COMPUTER ANIMATION
// ============================================
function setupComputerAnimation() {
    // Restart the typing animation every 4 seconds for continuous effect
    const codeLines = document.querySelectorAll('.code-line');
    
    setInterval(() => {
        codeLines.forEach((line, index) => {
            // Reset animation
            line.style.animation = 'none';
            // Force reflow
            void line.offsetWidth;
            // Restart animation with delay
            line.style.animation = `typeIn 0.5s ease-in forwards`;
            line.style.animationDelay = `${index * 0.5}s`;
        });
    }, 4000); // Restart every 4 seconds
}
