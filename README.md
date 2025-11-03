# LLM Chess Coach

A Data Science Capstone project exploring how Large Language Models (LLMs) engage with time-series constrained games like chess. This interactive chess application combines multiple AI agents to create a comprehensive learning experience that helps players improve through real-time coaching and analysis.

## Project Overview

This project investigates whether LLMs can understand chess rules, objectives, and dynamics through natural language instruction alone. The application features three distinct LLM agents working in harmony:

- **Coach LLM**: Analyzes player moves, provides feedback, and identifies key learning moments
- **Opponent LLM**: Plays against the user with human-like strategies
- **Commentator LLM**: Provides natural language descriptions of each move

## Features

### Interactive Chess Game
- Full-featured chess implementation with all standard rules
- Click-and-drag piece movement
- Visual board representation with piece highlights
- Move validation and check detection
- Support for special moves: castling, en passant, and pawn promotion

### AI Coaching
- **Real-time Analysis**: The Coach LLM analyzes each move and provides instant feedback
- **Learning Interventions**: Identifies blunders, missed tactics, and strategic errors
- **Interactive Q&A**: Players can ask questions and receive context-aware responses
- **Move Take-Back**: Option to undo moves when the coach identifies mistakes

### Multi-Agent Architecture
The application uses three specialized LLM agents:
- **Coach**: Provides educational feedback and strategic guidance
- **Opponent**: Plays competitive chess while maintaining human-like decision-making
- **Commentator**: Transforms chess notation into natural language descriptions

### Advanced Chess Features
- X-ray defense visualization
- Attack square tracking
- Castling rights management
- En passant detection
- Checkmate and stalemate detection
- 50-move rule and position repetition tracking
- Insufficient material detection

## Technical Architecture

### Stack
- **Frontend**: Streamlit
- **AI/LLM**: Google Gemini (Pro and Flash models)
- **Image Processing**: PIL/Pillow
- **Chess Logic**: Custom implementation with full rule support

### Key Components

- `chess_logic.py`: Core game engine with piece classes, board representation, and rule validation
- `chess_llm_functions.py`: LLM API integration for Coach, Opponent, and Commentator agents
- `app.py`: Main Streamlit application and UI logic
- `chess_app_functions.py`: Visual rendering and board interaction helpers
- `gemini_temporal_reasoning.py`: Metrics/evaluations of moves along with next move predictions
- `game_file_logger.py `: Cleaning and formatting game move history for metrics

### LLM Integration
The application uses Google's Gemini models with separate API keys for each agent:
- **Coach**: Gemini 2.5 Pro (complex analysis and strategic feedback)
- **Opponent**: Gemini 2.5 Pro (gameplay decisions)
- **Commentator**: Gemini 2.5 Flash (fast move commentary)

## Setup

### Prerequisites
- Python 3.8+
- Google AI API keys (4 keys needed)

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

3. Configure API keys:
Create a `.env` file in the project root with the following keys:
```env
GOOGLE_API_KEY=your_google_api_key
AI_OPPONENT_KEY=your_opponent_key
COACH_KEY=your_coach_key
COMMENTATOR_KEY=your_commentator_key
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
2. **Make Moves**: Click on a piece, then click on a destination square
3. **Receive Feedback**: After each move, the Coach LLM provides analysis and suggestions
4. **Interactive Learning**: Click pieces for visual move suggestions
5. **Ask Questions**: Use the chat input to ask the coach about strategy or position
6. **Interventions**: If you make a blunder, the coach will offer to let you take back the move

## Research Questions

This capstone project explores:
- Can LLMs learn complex game rules through natural language alone?
- How effectively do LLMs translate between structured game logic and natural language instruction?
- Can multi-agent LLM systems coordinate to provide comprehensive educational experiences?
- What are the limitations of LLMs in understanding temporal dependencies in strategic games?

## Project Structure

```
llm-games-project/
├── app.py                      # Main Streamlit application
├── chess_logic.py              # Core chess engine (683 lines)
├── chess_llm_functions.py      # LLM API integration
├── chess_app_functions.py       # UI and rendering helpers
├── gemini_temporal_reasoning.py # Metrics and move prediction
├── game_file_logger.py          # Dataset cleaning and formatting
├── requirements.txt             # Python dependencies
├── assets/                      # Chess piece images
│   ├── w_*.png                 # White pieces
│   └── b_*.png                 # Black pieces
└── README.md                    # This file
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
- ✓ Turn-by-turn coaching feedback
- ✓ Strategic position analysis
- ✓ Tactical error detection
- ✓ Move intervention system
- ✓ Question-answering interface
- ✓ Real-time board state narrative generation
- ✓ Stream response for natural interaction

### UI/UX
- ✓ Interactive click-to-move interface
- ✓ Visual piece selection highlighting
- ✓ Valid move indicators
- ✓ Check highlighting
- ✓ Move history display
- ✓ Board orientation switching
- ✓ Streaming coach responses

## License

This project is part of a Data Science Capstone course.

## Contributors

- Project: LLM Games Research Team
- Course: Data Science Capstone
