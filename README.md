# LLM Chess Coach

A Data Science Capstone project exploring how Large Language Models (LLMs) can engage with logic and reasoning games like chess. This interactive chess application combines multiple AI agents to create a comprehensive learning experience that helps players improve through real-time coaching and analysis.

## Project Overview

This project investigates whether LLMs can understand chess rules, objectives, and dynamics through natural language instruction. The application features two distinct LLM agent systems working in harmony:

- **Coach Agent**: Analyzes player moves using an "Offense-First" logic pipeline, provides real-time feedback, and identifies key learning moments
- **Opponent Agent**: Plays against the user with adaptive difficulty based on skill level, using multiple specialized personalities (best/human/blunder)

## Features

### Interactive Chess Game
- Full-featured chess implementation with all standard rules
- Click-to-move piece selection interface
- Visual board representation with piece highlights and valid move indicators
- Move validation and check detection
- Support for special moves: castling, en passant, and pawn promotion
- Board orientation switching (view from player's perspective)

### AI Coaching
- **Real-time Analysis**: The Coach Agent analyzes each move using "Offense-First" logic, prioritizing captures and forcing moves
- **Learning Interventions**: Identifies blunders, missed tactics, and strategic errors with specific feedback
- **Interactive Q&A**: Players can ask questions through a Router-based Q&A system with specialized tools:
  - Explain AI opponent's last move
  - Analyze current board position
  - Explain chess concepts
  - General conversation
- **Move Take-Back**: Option to undo moves when the coach identifies critical mistakes
- **Post-Game Analysis**: Comprehensive game summary with key learning moments

### Multi-Agent Architecture
The application uses two specialized LLM agent systems with multi-tool pipelines:

- **Coach Agent**: Provides educational feedback through a two-stage pipeline:
  - **Triage Analyst** (Gemini 2.5 Pro): Analyzes moves using "Offense-First" logic and returns verdicts
  - **Conversationalist** (Gemini 2.5 Flash): Translates verdicts into human-friendly responses
  - **Q&A Router** (Gemini 2.5 Flash): Routes questions to specialized analysis tools
  - **Post-Game Analyst** (Gemini 2.5 Pro): Provides comprehensive game summaries

- **Opponent Agent**: Plays competitive chess with adaptive difficulty:
  - **Router Agent** (Gemini 2.5 Flash): Selects personality based on skill level and board state
  - **Best Move Tool** (Gemini 2.5 Pro): Calculates optimal moves for advanced players
  - **Human-Like Move Tool** (Gemini 2.5 Flash): Plays solid, natural moves for intermediate players
  - **Teaching Blunder Tool** (Gemini 2.5 Flash): Creates learning opportunities for beginners
  - **Move Sanitizer Tool** (Gemini 2.5 Flash): Repairs malformed move strings for error recovery

### Advanced Chess Features
- **Tactical Analysis**: Automatic detection of pins, forks, skewers, and discovered attacks
- **Move Consequence Mapping**: Pre-computes all legal moves with full consequences (captures, checks, attacks, retaliation)
- **Tactical Threats Detection**: Real-time analysis of dangers including hanging pieces, bad trades, and pins
- **X-ray Defense Visualization**: Tracks attack squares including through friendly pieces
- **Attack Square Tracking**: Complete visibility of all piece threats
- **Castling Rights Management**: Tracks castling availability throughout the game
- **En Passant Detection**: Automatic detection and execution of en passant captures
- **Checkmate and Stalemate Detection**: Complete endgame state detection
- **Draw Detection**: 50-move rule, fivefold repetition, and insufficient material detection

## Technical Architecture

### Stack
- **Frontend**: Streamlit
- **AI/LLM**: Google Gemini (Pro and Flash models)
- **Image Processing**: PIL/Pillow
- **Chess Logic**: Custom implementation with full rule support

### Key Components

- `chess_logic.py`: Core game engine (976 lines) with piece classes, board representation, rule validation, tactical analysis, and move consequence mapping
- `chess_llm_functions.py`: LLM API integration with specialized tools for Coach and Opponent agents
- `coach_agent.py`: Orchestrator for Coach Agent pipelines (post-move analysis, Q&A, post-game)
- `ai_opponent_agent.py`: Orchestrator for Opponent Agent with router and specialist tools
- `app.py`: Main Streamlit application with state machine for game phases and parallel agent execution
- `chess_app_functions.py`: Visual rendering using PIL/Pillow and board interaction helpers

### LLM Integration
The application uses Google's Gemini models with a single API key (GOOGLE_API_KEY):
- **Model Selection**: Uses Gemini 2.5 Pro for complex analysis and Gemini 2.5 Flash for speed-sensitive tasks
- **Coach Agent**: 
  - Pro for Triage Analyst and Post-Game Analyst
  - Flash for Conversationalist and Q&A Router
- **Opponent Agent**:
  - Pro for Best Move Tool (optimal gameplay)
  - Flash for Router, Human-Like, Blunder, and Sanitizer tools

### Performance Optimizations
- **Parallel Agent Execution**: Coach and Opponent agents run simultaneously after each player move using ThreadPoolExecutor for reduced latency
- **Core Chess Definitions Knowledge Base**: Shared knowledge base of chess concepts (pins, forks, tempo, trades) used across all agents for consistent understanding
- **Move Consequence Pre-computation**: All legal moves are analyzed with full consequences before agent decision-making, providing ground-truth data
- **Tactical Threats Pre-computation**: Board state dangers are pre-calculated and provided as structured JSON to agents

## Setup

### Prerequisites
- Python 3.8+
- Google AI API key (single key for all agents)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd llm-games-project
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure API key:
Create a `.env` file in the project root with your Google AI API key:
```env
GOOGLE_API_KEY=your_google_api_key
```

Alternatively, set the environment variable directly:
```bash
export GOOGLE_API_KEY=your_google_api_key
```

4. Ensure the `assets/` folder contains chess piece images:
- `w_pawn.png`, `w_rook.png`, `w_knight.png`, `w_bishop.png`, `w_queen.png`, `w_king.png`
- `b_pawn.png`, `b_rook.png`, `b_knight.png`, `b_bishop.png`, `b_queen.png`, `b_king.png`

### Running the Application

```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

## Usage

1. **Start a Game**: Choose to play as White (moves first) or Black (AI moves first)
2. **Select Skill Level**: Choose beginner, intermediate, or advanced to adjust opponent difficulty
3. **Make Moves**: Click on a piece (highlighted), then click on a destination square (green dots show valid moves)
4. **Receive Feedback**: After each move, Coach Joey provides instant analysis using "Offense-First" logic
5. **Interactive Learning**: 
   - Click pieces to see valid moves highlighted
   - Use the chat to ask questions about strategy, concepts, or the current position
   - Coach Joey uses specialized Q&A tools to provide accurate, context-aware answers
6. **Interventions**: If you make a critical blunder, the coach will offer to let you take back the move
7. **Post-Game**: After the game ends, receive a comprehensive summary with key learning moments

## Research Questions

This capstone project explores:
- Can LLMs learn complex game rules through natural language alone?
- How effectively do LLMs translate between structured game logic and natural language instruction?
- Can multi-agent LLM systems coordinate to provide comprehensive educational experiences?
- What are the limitations of LLMs in understanding temporal dependencies in strategic games?

## Project Structure

```
llm-games-project/
├── app.py                         # Main Streamlit application (515 lines)
├── chess_logic.py                 # Core chess engine (976 lines)
├── chess_llm_functions.py         # LLM API integration with all tools (906 lines)
├── coach_agent.py                 # Coach Agent orchestrator (107 lines)
├── ai_opponent_agent.py           # Opponent Agent orchestrator (97 lines)
├── chess_app_functions.py         # UI and rendering helpers (134 lines)
├── user_tracking_architecture.py  # User analytics (optional)
├── requirements.txt               # Python dependencies
├── assets/                        # Chess piece images
│   ├── w_*.png                    # White pieces
│   └── b_*.png                    # Black pieces
└── README.md                      # This file
```

## Features Implemented

### Chess Rules
- ✓ All piece movements and captures
- ✓ Check and checkmate detection
- ✓ Stalemate detection
- ✓ Castling (kingside and queenside)
- ✓ En passant
- ✓ Pawn promotion
- ✓ 50-move rule tracking
- ✓ Threefold repetition detection
- ✓ Insufficient material draws

### AI Capabilities
- ✓ "Offense-First" coaching logic prioritizing captures and forcing moves
- ✓ Triage Analyst tool for systematic move evaluation
- ✓ Conversational Coach Joey for human-friendly feedback
- ✓ Q&A Router with specialized analysis tools
- ✓ Strategic position analysis with tactical threats detection
- ✓ Tactical error detection (blunders, bad trades, hanging pieces)
- ✓ Move intervention system with take-back option
- ✓ Question-answering interface with context-aware responses
- ✓ Post-game analysis with key learning moments
- ✓ Skill-based opponent difficulty (beginner/intermediate/advanced)
- ✓ Adaptive opponent personality (best/human/blunder)
- ✓ Move sanitizer for error recovery

### UI/UX
- ✓ Interactive click-to-move interface
- ✓ Visual piece selection highlighting (blue)
- ✓ Valid move indicators (green dots)
- ✓ Check highlighting (red)
- ✓ Opponent thinking indicator (yellow border)
- ✓ Move history display
- ✓ Board orientation switching (player perspective)
- ✓ Skill level selector
- ✓ Real-time coach chat interface
- ✓ Opponent reasoning display with personality avatars

## License

This project is part of UMKC - Masters of Data Science Capstone course. To be presented at the Hack-A-Roo event on November 14th.

## Contributors

- Jack Lin
- Joseph Marinello
