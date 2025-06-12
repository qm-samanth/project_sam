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
            
            // Check if we have a natural language response
            if (data.natural_response) {
                // Display the natural language response with clickable links
                appendNaturalResponse(data.natural_response);
            } else if (data.results && data.results.length > 0) {
                // Fallback to structured results if no natural response
                // Sort results by LLM relevance score first, then by relevance score
                data.results.sort((a, b) => {
                    // If both have LLM scores, use those
                    if (a.llm_relevance_score && b.llm_relevance_score) {
                        return (b.llm_relevance_score || 0) - (a.llm_relevance_score || 0);
                    }
                    // Fallback to original relevance score
                    return (b.relevance_score || 0) - (a.relevance_score || 0);
                });
                
                // Display multiple results if available
                const resultCount = data.results.length;
                appendMessage(`Found ${resultCount} relevant result${resultCount > 1 ? 's' : ''}:`, 'bot-message');
                
                data.results.forEach((result, index) => {
                    // Create a structured result display
                    appendStructuredResult(result);
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

    function appendStructuredResult(result) {
        const resultContainer = document.createElement('div');
        resultContainer.classList.add('message', 'bot-message', 'structured-result');
        
        // Name as clickable link
        if (result.name) {
            const nameElement = document.createElement('div');
            nameElement.classList.add('result-name');
            
            if (result.url_path && result.url_path !== "N/A") {
                const link = document.createElement('a');
                link.href = result.url_path;
                link.target = '_blank';
                link.textContent = result.name;
                link.classList.add('result-link');
                nameElement.appendChild(link);
            } else {
                nameElement.textContent = result.name;
            }
            resultContainer.appendChild(nameElement);
        }
        
        // Functionality/Common Tasks
        if (result.common_tasks && result.common_tasks.length > 0) {
            const functionalityElement = document.createElement('div');
            functionalityElement.classList.add('result-functionality');
            functionalityElement.innerHTML = `<strong>Common Tasks:</strong>`;
            
            const tasksList = document.createElement('ul');
            tasksList.classList.add('common-tasks-list');
            
            result.common_tasks.forEach(task => {
                const taskItem = document.createElement('li');
                taskItem.textContent = task.label;
                tasksList.appendChild(taskItem);
            });
            
            functionalityElement.appendChild(tasksList);
            resultContainer.appendChild(functionalityElement);
        } else if (result.description) {
            // Fallback to description if no common_tasks
            const functionalityElement = document.createElement('div');
            functionalityElement.classList.add('result-functionality');
            functionalityElement.innerHTML = `<strong>Functionality:</strong> ${result.description}`;
            resultContainer.appendChild(functionalityElement);
        }
        
        // Relevance score
        if (result.relevance_score) {
            const relevancePercent = (result.relevance_score * 100).toFixed(1);
            const relevanceElement = document.createElement('div');
            relevanceElement.classList.add('result-relevance');
            relevanceElement.textContent = `Relevance: ${relevancePercent}%`;
            resultContainer.appendChild(relevanceElement);
        }
        
        chatMessages.appendChild(resultContainer);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendNaturalResponse(naturalResponse) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', 'bot-message', 'natural-response');
        
        // Convert markdown links to clickable HTML links
        const htmlContent = naturalResponse.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" class="result-link">$1</a>');
        
        messageElement.innerHTML = htmlContent;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
