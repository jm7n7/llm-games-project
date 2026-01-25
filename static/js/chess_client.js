document.addEventListener('DOMContentLoaded', () => {
    // --- State ---
    let selectedSquare = null;
    let validMoves = []; // Array of coordinates [r, c]
    let isPlayerTurn = false; // Synced with backend
    let playerColor = 'white'; // Default

    // --- Elements ---
    const boardElement = document.getElementById('chess-board');
    const newGameBtn = document.getElementById('new-game-btn');
    const statusElement = document.getElementById('game-status');
    const turnIndicator = document.getElementById('turn-indicator');

    // AI Reasoning
    const aiReasoningModal = document.getElementById('ai-reasoning-modal');
    const aiReasoningText = document.getElementById('ai-reasoning-text');

    // Modals
    const promotionModal = document.getElementById('promotion-modal');
    const promoBtns = document.querySelectorAll('.promo-btn');
    const gameOverModal = document.getElementById('game-over-modal');
    const gameOverTitle = document.getElementById('game-over-title');
    const gameOverMessage = document.getElementById('game-over-message');
    const modalNewGameBtn = document.getElementById('modal-new-game-btn');

    // --- Initialization ---
    // define default or fetch?
    initBoard();
    fetchGameState();

    // --- Event Listeners ---
    newGameBtn.addEventListener('click', startNewGame);
    modalNewGameBtn.addEventListener('click', () => {
        gameOverModal.classList.add('hidden');
        startNewGame();
    });

    promoBtns.forEach(btn => {
        btn.addEventListener('click', (e) => handlePromotionSelection(e.target.dataset.piece));
    });

    // Close AI Reasoning
    const closeReasoningBtn = document.getElementById('close-reasoning-btn');
    if (closeReasoningBtn) {
        closeReasoningBtn.addEventListener('click', () => {
            aiReasoningModal.classList.add('hidden');
        });
    }

    // --- Analysis Logic ---
    const analyzeBtn = document.getElementById('modal-analyze-btn');
    const analysisModal = document.getElementById('analysis-modal');
    const analysisContent = document.getElementById('analysis-content');
    const closeAnalysisBtn = document.getElementById('close-analysis-btn');

    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', async () => {
            analyzeBtn.innerText = "Analyzing... 🕒";
            analyzeBtn.disabled = true;

            try {
                const response = await fetch('/api/analyze_game', { method: 'POST' });
                const data = await response.json();

                if (data.status === 'success' && data.analysis) {
                    analysisContent.innerText = data.analysis.message || JSON.stringify(data.analysis, null, 2);
                    analysisModal.classList.remove('hidden');
                } else {
                    alert("Could not generate analysis. Try again!");
                }
            } catch (error) {
                console.error("Analysis error:", error);
                alert("Error connecting to Coach Joey.");
            } finally {
                analyzeBtn.innerText = "Analyze Game 🧠";
                analyzeBtn.disabled = false;
            }
        });
    }

    if (closeAnalysisBtn) {
        closeAnalysisBtn.addEventListener('click', () => {
            analysisModal.classList.add('hidden');
        });
    }

    // --- Functions ---

    function initBoard() {
        boardElement.innerHTML = '';
        for (let r = 0; r < 8; r++) {
            for (let c = 0; c < 8; c++) {
                const square = document.createElement('div');
                square.classList.add('square');

                // Determine light/dark
                const isLight = (r + c) % 2 === 0;
                square.classList.add(isLight ? 'light' : 'dark');

                // Save PHYSICAL coordinates (always 0-7 top-left origin)
                square.dataset.physRow = r;
                square.dataset.physCol = c;

                // We pass physical coords to handler
                square.addEventListener('click', () => handleSquareClick(r, c));
                boardElement.appendChild(square);
            }
        }
    }

    // Helper: Map Logical (Game) Coords -> Physical (Grid) Coords
    // Used for placing pieces and highlighting
    function getSquareByLogicalCoords(logR, logC) {
        let physR = logR;
        let physC = logC;

        if (playerColor === 'black') {
            physR = 7 - logR;
            physC = 7 - logC;
        }
        // Use attribute selector
        return document.querySelector(`.square[data-phys-row="${physR}"][data-phys-col="${physC}"]`);
    }

    // Helper: Map Physical (Click) Coords -> Logical (Game) Coords
    // Used for interpreting clicks
    function getLogicalCoords(physR, physC) {
        if (playerColor === 'black') {
            return [7 - physR, 7 - physC];
        }
        return [physR, physC];
    }

    async function startNewGame() {
        // Read color selection
        const colorInput = document.querySelector('input[name="playerColor"]:checked');
        playerColor = colorInput ? colorInput.value : 'white';

        // Read skill level
        const skillInput = document.querySelector('input[name="skillLevel"]:checked');
        const skillLevel = skillInput ? skillInput.value : 'beginner';

        try {
            const response = await fetch('/api/new_game', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    player_color: playerColor,
                    skill_level: skillLevel
                })
            });
            const data = await response.json();
            if (data.status === 'success') {
                gameOverModal.classList.add('hidden');
                aiReasoningModal.classList.add('hidden'); // Reset AI dialog
                // Clear board locally to force re-render with correct rotation if changed
                initBoard();
                fetchGameState();
            }
        } catch (error) {
            console.error("Error starting game:", error);
        }
    }

    async function fetchGameState() {
        try {
            const response = await fetch('/api/state');
            if (response.status === 404) {
                statusElement.innerText = "No active game.";
                return;
            }
            const data = await response.json();

            // If page refreshed, we might lose playerColor state if we don't save/load it.
            // Ideally backend sends 'player_color' in state.
            // For now, let's assume default white or user keeps selection.
            // We can infer it? No.
            // TODO: Add player_color to /api/state response for persistence.

            renderBoard(data.grid, data.in_check, data.turn);
            updateStatus(data);
        } catch (error) {
            console.error("Error fetching state:", error);
        }
    }

    function renderBoard(grid, inCheck, turnColor) {
        // Clear global check highlights first (simplest way, low cost)
        document.querySelectorAll('.square.in-check').forEach(el => el.classList.remove('in-check'));

        for (let r = 0; r < 8; r++) {
            for (let c = 0; c < 8; c++) {
                const cellData = grid[r][c];
                const square = getSquareByLogicalCoords(r, c);

                if (!square) continue;

                // 1. Handle Piece
                const existingPiece = square.querySelector('.piece');

                if (cellData) {
                    // We need a piece here.
                    const colorPrefix = cellData.color === 'white' ? 'w' : 'b';
                    const filename = `${colorPrefix}_${cellData.type}.png`;
                    const bgUrl = `url("/static/assets/${filename}")`; // Note quotes for consistency

                    if (existingPiece) {
                        // Check if it's the SAME piece image
                        // browsers might normalize url(), so strict string comparison might be tricky.
                        // Let's use a data attribute for robust checking.
                        if (existingPiece.dataset.filename !== filename) {
                            existingPiece.style.backgroundImage = bgUrl;
                            existingPiece.dataset.filename = filename;
                        }
                    } else {
                        // Create new piece
                        const piece = document.createElement('div');
                        piece.classList.add('piece');
                        piece.style.backgroundImage = bgUrl;
                        piece.dataset.filename = filename;
                        square.appendChild(piece);
                    }

                    // 2. Handle Check Highlight
                    if (inCheck && cellData.type === 'king' && cellData.color === turnColor) {
                        square.classList.add('in-check');
                    }

                } else {
                    // No piece here. Remove if exists.
                    if (existingPiece) {
                        existingPiece.remove();
                    }
                }
            }
        }
    }

    // Track transition timeout to prevent overlapping animations
    let transitionTimeout = null;

    function updateStatus(data) {
        // Ensure playerColor is valid
        if (!playerColor) {
            const colorInput = document.querySelector('input[name="playerColor"]:checked');
            playerColor = colorInput ? colorInput.value : 'white';
        }

        const isMyTurn = data.turn === playerColor;
        const moverName = isMyTurn ? (data.username || "Player") : "AI";
        const turnColorFormatted = data.turn.charAt(0).toUpperCase() + data.turn.slice(1);

        // Status Text
        let newTurnText = `${turnColorFormatted}'s Turn`;
        let newStatusText = moverName;

        if (data.status_message.includes("(in check)")) {
            newStatusText += " (in check)";
        } else if (data.status_message.toLowerCase().includes("promotion")) {
            newStatusText += " - Promotion Pending";

            // If it's my turn (and I am the one promoting), show modal
            // Note: In pending state, backend 'turn' is still the player who moved.
            if (data.turn === playerColor) {
                const promotionModal = document.getElementById('promotion-modal');
                if (promotionModal) promotionModal.classList.remove('hidden');
            }
        }

        // Add pipe separator visually
        newStatusText = `| ${newStatusText}`;

        // Check if text actually changed to avoid unnecessary fades
        if (turnIndicator.innerText !== newTurnText || statusElement.innerText !== newStatusText) {

            // Clear any pending timeout involved in a running transition
            if (transitionTimeout) {
                clearTimeout(transitionTimeout);
                transitionTimeout = null;
            }

            // Fade Out
            turnIndicator.classList.add('fade-out');
            statusElement.classList.add('fade-out');

            transitionTimeout = setTimeout(() => {
                // Update Text
                turnIndicator.innerText = newTurnText;
                statusElement.innerText = newStatusText;

                // Fade In
                turnIndicator.classList.remove('fade-out');
                statusElement.classList.remove('fade-out');
                transitionTimeout = null;
            }, 500); // 500ms matches CSS transition
        }

        if (data.game_over) {
            isPlayerTurn = false;
            statusElement.innerText = data.status_message; // Show final result
            showGameOver(data);
            return;
        }

        // Handle Turn Logic
        if (isMyTurn) {
            isPlayerTurn = true;
        } else {
            isPlayerTurn = false;
            // If it is NOT my turn (and game not over), it's AI's turn.
            // Triggers only if we are not already waiting for AI and NOT currently handling a move
            if (!statusElement.innerText.includes("Moving") && !handlingMove) {
                triggerAIMoveOnly();
            }
        }

    }

    function showGameOver(data) {
        gameOverModal.classList.remove('hidden');

        if (data.winner === 'draw') {
            gameOverTitle.innerText = "Game Drawn";
            gameOverMessage.innerText = data.status_message;
        } else if (data.winner) {
            const winnerName = data.winner.charAt(0).toUpperCase() + data.winner.slice(1);
            gameOverTitle.innerText = `${winnerName} Wins!`;
            gameOverMessage.innerText = `Checkmate! ${data.status_message}`;
        }
    }

    async function handleSquareClick(physR, physC) {
        if (!isPlayerTurn) return;

        // Convert physical to logical
        const [r, c] = getLogicalCoords(physR, physC);

        const square = getSquareByLogicalCoords(r, c); // Get the element for visual checking
        const hasPiece = square.querySelector('.piece');

        // 1. If nothing selected, select piece
        if (!selectedSquare) {
            if (hasPiece) {
                await selectSquare(r, c);
            }
            return;
        }

        // 2. If something selected...
        const startPos = [selectedSquare.r, selectedSquare.c];
        const endPos = [r, c];

        // If clicked same square, deselect
        if (startPos[0] === endPos[0] && startPos[1] === endPos[1]) {
            deselectSquare();
            return;
        }

        // If clicked another friendly piece, switch selection
        if (hasPiece) {
            const isValidMove = validMoves.some(m => m[0] === r && m[1] === c);
            if (!isValidMove) {
                await selectSquare(r, c);
                return;
            }
        }

        // Try to move
        if (validMoves.some(m => m[0] === r && m[1] === c)) {
            await makeMove(startPos, endPos);
            deselectSquare();
        } else {
            deselectSquare();
        }
    }

    async function selectSquare(r, c) {
        if (selectedSquare) deselectSquare();
        selectedSquare = { r, c };

        const sq = getSquareByLogicalCoords(r, c);
        if (sq) sq.classList.add('selected');

        try {
            const response = await fetch('/api/legal_moves', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ start: [r, c] })
            });
            const data = await response.json();
            if (data.status === 'success') {
                validMoves = data.moves;
                showValidMoves();
            }
        } catch (e) {
            console.error("Error fetching moves", e);
        }
    }

    function showValidMoves() {
        validMoves.forEach(move => {
            const [r, c] = move;
            const sq = getSquareByLogicalCoords(r, c);
            if (sq) sq.classList.add('valid-move');
        });
    }

    function deselectSquare() {
        if (selectedSquare) {
            const sq = getSquareByLogicalCoords(selectedSquare.r, selectedSquare.c);
            if (sq) sq.classList.remove('selected');
            selectedSquare = null;
        }
        validMoves.forEach(move => {
            const [r, c] = move;
            const sq = getSquareByLogicalCoords(r, c);
            if (sq) sq.classList.remove('valid-move');
        });
        validMoves = [];
    }

    // Flag to prevent updateStatus from triggering AI while we are processing a move
    let handlingMove = false;

    async function makeMove(start, end) {
        handlingMove = true;
        try {
            // 1. Optimistic UI Update
            const startSq = getSquareByLogicalCoords(start[0], start[1]);
            const endSq = getSquareByLogicalCoords(end[0], end[1]);
            const piece = startSq.querySelector('.piece');

            if (piece && endSq) {
                const captured = endSq.querySelector('.piece');
                if (captured) captured.remove();
                endSq.appendChild(piece);
            }

            // Show "Thinking" status
            statusElement.innerText = "Coach is thinking... 🤔";
            statusElement.classList.add('pulse');
            aiReasoningModal.classList.remove('hidden');
            aiReasoningText.innerText = "Analyzing...";

            const response = await fetch('/api/process_move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ start, end })
            });
            const data = await response.json();

            statusElement.classList.remove('pulse');

            if (data.status === 'success') {
                // 1. Update Board State (Human Move Confirmed)
                fetchGameState();

                // 2. Handle Coach Feedback
                const feedback = data.coach_feedback;
                if (feedback && feedback.message) {
                    addMessage(feedback.message, 'coach');
                }

                // 3. Handle Intervention
                if (feedback && feedback.type === 'intervention') {
                    showInterventionModal(feedback.message);
                    return; // Stop here. Pending AI move is stored in backend.
                }

                // 4. Handle AI Move (if no intervention)
                if (data.ai_move) {
                    if (data.ai_reasoning) {
                        aiReasoningText.innerText = `"${data.ai_reasoning}"`;
                    }
                    statusElement.innerText = "AI Moving...";
                    // Delay slightly for effect
                    setTimeout(() => executeAIMove(), 800);
                } else if (!data.game_over && !data.status_message.includes("Promotion")) {
                    // Start of game / No AI move returned? (Shouldn't happen in loop)
                    aiReasoningModal.classList.add('hidden');
                }

            } else {
                console.warn("Invalid move:", data.message);
                fetchGameState(); // Revert
                statusElement.innerText = "Invalid Move";
                aiReasoningModal.classList.add('hidden');
            }
        } catch (error) {
            console.error("Error making move:", error);
            fetchGameState();
        } finally {
            handlingMove = false;
        }
    }

    async function executeAIMove() {
        // Calls the endpoint to APPLY the pending AI move
        try {
            const response = await fetch('/api/confirm_ai_move', { method: 'POST' });
            const data = await response.json();

            if (data.status === 'success') {
                fetchGameState(); // Update board, AI turn ends, Human turn begins
                // Clear AI thinking text after move
                aiReasoningModal.classList.add('hidden');
            } else {
                console.error("AI Move Failed:", data.message);
                statusElement.innerText = "AI Error: " + data.message;
            }
        } catch (e) {
            console.error("Execute AI Move Network Error:", e);
        }
    }

    async function triggerAIMoveOnly() {
        // Only used for Start of Game (Black) or Resuming Unfinished Turn
        statusElement.innerText = "AI is thinking... 🤖";
        statusElement.classList.add('pulse');
        aiReasoningModal.classList.remove('hidden');
        aiReasoningText.innerText = "Thinking...";

        try {
            const response = await fetch('/api/ai_turn', { method: 'POST' });
            const data = await response.json();

            statusElement.classList.remove('pulse');

            if (data.status === 'success') {
                // Handle Coach Feedback (Unlikely here, but possible)
                if (data.coach_feedback && data.coach_feedback.message) {
                    addMessage(data.coach_feedback.message, 'coach');
                }

                if (data.ai_move) {
                    if (data.ai_reasoning) aiReasoningText.innerText = `"${data.ai_reasoning}"`;
                    statusElement.innerText = "AI Moving...";
                    setTimeout(() => executeAIMove(), 800);
                }
            } else {
                statusElement.innerText = "AI Error";
            }
        } catch (e) {
            console.error(e);
            statusElement.innerText = "Error";
        }
    }

    const interventionModal = document.getElementById('intervention-modal');
    const interventionMessage = document.getElementById('intervention-message');
    const interventionIgnoreBtn = document.getElementById('intervention-ignore-btn');
    const interventionUndoBtn = document.getElementById('intervention-undo-btn');

    if (interventionIgnoreBtn) {
        interventionIgnoreBtn.addEventListener('click', () => {
            interventionModal.classList.add('hidden');
            executeAIMove();
        });
    }

    if (interventionUndoBtn) {
        interventionUndoBtn.addEventListener('click', async () => {
            interventionModal.classList.add('hidden');
            await fetch('/api/undo_move', { method: 'POST' });
            fetchGameState(); // Revert board
        });
    }

    function showInterventionModal(message) {
        interventionMessage.innerText = message;
        interventionModal.classList.remove('hidden');
    }

    async function handlePromotionSelection(pieceName) {
        try {
            const response = await fetch('/api/promote', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ promotion: pieceName })
            });
            const data = await response.json();

            if (data.status === 'success') {
                promotionModal.classList.add('hidden');
                fetchGameState();
            }
        } catch (error) {
            console.error("Error promoting:", error);
        }
    }

    // --- Chat Logic ---
    const chatInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const chatHistory = document.getElementById('chat-history');

    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        // Add user message
        addMessage(text, 'user');
        chatInput.value = '';

        // Show typing indicator
        const typingId = addMessage("Thinking...", 'coach');

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await response.json();

            const typingEl = document.getElementById(typingId);
            if (typingEl) typingEl.remove();

            if (data.status === 'success') {
                addMessage(data.response, 'coach');
            } else {
                addMessage("I'm having trouble connecting to the matrix.", 'coach');
            }
        } catch (error) {
            console.error("Chat error:", error);
        }
    }

    function addMessage(text, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('chat-message', `message-${sender}`);
        msgDiv.innerText = text;
        const id = `msg-${Date.now()}`;
        msgDiv.id = id;

        chatHistory.appendChild(msgDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        return id;
    }

}); // End DOMContentLoaded
