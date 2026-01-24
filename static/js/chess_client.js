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

        try {
            const response = await fetch('/api/new_game', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ player_color: playerColor })
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
        const moverName = isMyTurn ? "Player" : "AI";
        const turnColorFormatted = data.turn.charAt(0).toUpperCase() + data.turn.slice(1);

        // Status Text
        let newTurnText = `${turnColorFormatted}'s Turn`;
        let newStatusText = moverName;

        if (data.status_message.includes("(in check)")) {
            newStatusText += " (in check)";
        } else if (data.status_message.toLowerCase().includes("promotion")) {
            newStatusText += " - Promotion Pending";
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

        isPlayerTurn = true;

        if (data.game_over) {
            isPlayerTurn = false;
            statusElement.innerText = data.status_message; // Show final result
            showGameOver(data);
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

    async function makeMove(start, end) {
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
            statusElement.innerText = "AI is thinking... 🤖";
            statusElement.classList.add('pulse');

            // Show AI Reasoning Modal (Thinking state)
            aiReasoningModal.classList.remove('hidden');
            aiReasoningText.innerText = "Thinking...";

            const response = await fetch('/api/process_move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ start, end })
            });
            const data = await response.json();

            // Remove pulse
            statusElement.classList.remove('pulse');

            if (data.status === 'success') {
                // Move Valid
                fetchGameState();

                const feedback = data.coach_feedback;
                if (feedback && feedback.message) {
                    addMessage(feedback.message, 'coach');
                }

                // Update Reasoning Text
                if (data.ai_reasoning) {
                    aiReasoningText.innerText = `"${data.ai_reasoning}"`;
                } else {
                    aiReasoningText.innerText = "Calculated best response.";
                }

                if (feedback.type === 'intervention') {
                    // --- INTERVENTION ---
                    showInterventionModal(feedback.message);
                } else if (data.ai_move) {
                    // --- NO INTERVENTION ---
                    statusElement.innerText = "AI Moving...";
                    setTimeout(() => {
                        executeAIMove();
                    }, 800);
                }
            } else {
                console.warn("Invalid move:", data.message);
                fetchGameState();
                statusElement.innerText = "Invalid Move";
                aiReasoningModal.classList.add('hidden'); // Hide if invalid
            }
        } catch (error) {
            console.error("Error making move:", error);
            fetchGameState();
        }
    }

    async function executeAIMove() {
        // Calls the endpoint to APPLY the pending AI move
        const response = await fetch('/api/confirm_ai_move', { method: 'POST' });
        const data = await response.json();
        if (data.status === 'success') {
            fetchGameState();
        }
    }

    function showInterventionModal(message) {
        // Reuse Game Over or Promotion modal style for simplicity?
        // Or inject a new one. Let's reuse Promotion modal structure via JS if possible, 
        // logic is safer to just create a dynamic overlay or use `confirm`.
        // `confirm` is blocking/ugly. Let's assume we have an 'intervention-modal'.

        // Quick Hack: Modify Game Over modal content temporarily
        gameOverTitle.innerText = "Wait! Coach Intervention 🛑";
        gameOverMessage.innerText = message;
        modalNewGameBtn.innerText = "Ignore & Continue";

        // Add a secondary button for "Undo"
        let undoBtn = document.getElementById('modal-undo-btn');
        if (!undoBtn) {
            undoBtn = document.createElement('button');
            undoBtn.id = 'modal-undo-btn';
            undoBtn.className = 'btn-primary'; // Style it
            undoBtn.style.backgroundColor = '#666'; // Grey logic
            undoBtn.style.marginLeft = '10px';
            undoBtn.innerText = "Take Back Move";
            modalNewGameBtn.parentNode.appendChild(undoBtn);

            undoBtn.addEventListener('click', async () => {
                await fetch('/api/undo_move', { method: 'POST' });
                gameOverModal.classList.add('hidden');
                fetchGameState(); // Revert board
            });
        }

        // Override "Ignore" behavior
        modalNewGameBtn.onclick = async () => {
            gameOverModal.classList.add('hidden');
            // Restore default behavior
            modalNewGameBtn.onclick = () => { gameOverModal.classList.add('hidden'); startNewGame(); };
            executeAIMove();
        };

        gameOverModal.classList.remove('hidden');
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
