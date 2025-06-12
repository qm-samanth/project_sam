document.addEventListener('DOMContentLoaded', () => {
    const openChatButton = document.getElementById('open-chat-button');
    const chatWidget = document.getElementById('chat-widget');
    const closeChatButton = document.getElementById('close-chat');
    const sendButton = document.getElementById('send-button');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');

    openChatButton.addEventListener('click', () => {
        chatWidget.style.display = 'flex';
        openChatButton.style.display = 'none';
    });

    closeChatButton.addEventListener('click', () => {
        chatWidget.style.display = 'none';
        openChatButton.style.display = 'block';
    });

    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    function sendMessage() {
        const messageText = chatInput.value.trim();
        if (messageText === '') return;

        appendMessage(messageText, 'user-message');
        chatInput.value = '';

        // Simulate bot response (replace with actual API call)
        fetchBackendResponse(messageText);
    }

    function appendMessage(text, className) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', className);
        messageElement.textContent = text;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to the bottom
    }

    async function fetchBackendResponse(query) {
        appendMessage("Thinking...", "bot-message"); // Temporary thinking message
        try {
            // Adjust the URL to your backend endpoint
            const response = await fetch('http://127.0.0.1:5000/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: query }), // Changed 'query' to 'text'
            });

            // Remove "Thinking..." message
            const thinkingMessage = chatMessages.querySelector(".bot-message:last-child");
            if (thinkingMessage && thinkingMessage.textContent === "Thinking...") {
                chatMessages.removeChild(thinkingMessage);
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: "Unknown error" }));
                console.error('Backend error:', response.status, errorData);
                appendMessage(`Error: ${errorData.error || response.statusText}`, 'bot-message');
                return;
            }

            const data = await response.json();
            
            if (data.results && data.results.length > 0) {
                // Display multiple results if available
                const resultCount = data.results.length;
                appendMessage(`Found ${resultCount} relevant result${resultCount > 1 ? 's' : ''}:`, 'bot-message');
                
                data.results.forEach((result, index) => {
                    let botReply = "";
                    
                    if (result.name && result.description) {
                        botReply = `${result.name}: ${result.description}`;
                    } else if (result.name) {
                        botReply = result.name;
                    } else if (result.description) {
                        botReply = result.description;
                    } else {
                        botReply = "No displayable content found for this result.";
                    }
                    
                    // Add URL if available
                    if (result.url_path && result.url_path !== "N/A") {
                        botReply += ` (Link: ${result.url_path})`;
                    }
                    
                    // Add relevance score
                    if (result.relevance_score) {
                        const relevancePercent = (result.relevance_score * 100).toFixed(1);
                        botReply += ` [Relevance: ${relevancePercent}%]`;
                    }
                    
                    appendMessage(botReply, 'bot-message');
                });
            } else if (data.message) { 
                // Handle cases where backend sends a direct message (e.g., "No results found")
                appendMessage(data.message, 'bot-message');
            } else {
                appendMessage("No relevant information found.", 'bot-message');
            }

        } catch (error) {
            console.error('Error fetching from backend:', error);
             // Remove "Thinking..." message if it's still there after an error
            const thinkingMessage = chatMessages.querySelector(".bot-message:last-child");
            if (thinkingMessage && thinkingMessage.textContent === "Thinking...") {
                chatMessages.removeChild(thinkingMessage);
            }
            appendMessage('Sorry, I encountered an error trying to reach the server.', 'bot-message');
        }
    }
});
