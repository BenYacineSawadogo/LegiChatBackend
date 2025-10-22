document.addEventListener("DOMContentLoaded", () => {
    const chat = document.getElementById("chat");
    const questionInput = document.getElementById("question");
    const askButton = document.getElementById("ask-button");
    const toggleSidebar = document.getElementById("toggle-sidebar");
    const sidebar = document.getElementById("sidebar");
    const resetButton = document.getElementById("reset-button");

    function appendMessage(message, className) {
        const div = document.createElement("div");
        div.className = className;
        div.innerHTML = message;
        chat.appendChild(div);
        chat.scrollTop = chat.scrollHeight;
    }

    function formatText(text) {
        let cleaned = text.replace(/\*\*(.*?)\*\*/g, "$1");
        cleaned = cleaned.replace(/\*(.*?)\*/g, "$1");
        cleaned = cleaned.replace(/\*/g, "");
        cleaned = cleaned.replace(/\n/g, "<br>");
        return cleaned;
    }

    function setLoading(isLoading) {
        if (isLoading) {
            askButton.disabled = true;
            askButton.textContent = "Génération...";
        } else {
            askButton.disabled = false;
            askButton.textContent = "Envoyer";
        }
    }

    askButton.onclick = async () => {
        const question = questionInput.value.trim();
        if (!question) return;

        appendMessage(question, "user-message");
        questionInput.value = "";
        setLoading(true);

        const botMessageDiv = document.createElement("div");
        botMessageDiv.className = "bot-message";

        const typingIndicator = document.createElement("div");
        typingIndicator.className = "typing";
        typingIndicator.innerHTML = "<span></span><span></span><span></span>";

        botMessageDiv.appendChild(typingIndicator);
        chat.appendChild(botMessageDiv);
        chat.scrollTop = chat.scrollHeight;

        try {
            const response = await fetch("/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question }),
            });

            if (!response.body) {
                botMessageDiv.innerHTML = "Erreur : Pas de corps de réponse.";
                setLoading(false);
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let done = false;
            let fullResponse = "";

            // Supprime les "..." et commence à afficher la réponse
            botMessageDiv.innerHTML = "";

            while (!done) {
                const { value, done: doneReading } = await reader.read();
                done = doneReading;
                if (value) {
                    const chunk = decoder.decode(value, { stream: true });
                    if (chunk.includes("[DONE]")) break;
                    fullResponse += chunk;
                    botMessageDiv.innerHTML = formatText(fullResponse);
                    chat.scrollTop = chat.scrollHeight;
                }
            }
        } catch (error) {
            botMessageDiv.innerHTML = "Erreur lors de la connexion au serveur.";
        } finally {
            setLoading(false);
        }
    };

    // Réinitialisation du chat
    resetButton.onclick = () => {
        chat.innerHTML = "";
    };

    // Affichage/Masquage de la sidebar
    toggleSidebar.onclick = () => {
        sidebar.classList.toggle("hidden");
    };
});
