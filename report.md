# RooChess: Humanistic Learning with LLMs

**Course:** CS 5588 – Video LLMs for Real-Time Temporal and Spatial Reasoning

**Track B:** Temporal Reasoning

**Team:** Joseph Marinello & Jack Lin


---

## Domain Focus & Setup Summary

RooChess extends our semester-long human-centric LLM learning framework from our plans indicated in PA 1 - PA 4.
The system enables a player to interact with Gemini LLMs through a Streamlit interface, combining:

* Temporal reasoning: Gemini 2.5-Flash identifies and predicts chess moves across frames.
* Stockfish evaluation: Provides objective quantitative feedback per move.
* Coach LLM: Supplies turn-by-turn reflection and strategic guidance.
* Commentator LLM: Translates move data into natural-language play-by-play sentences.
* Opponent LLM: Chooses responses from legal moves for human-like play.

This prototype functions as an interactive learning environment where temporal reasoning is demonstrated through multi-frame move analysis and prediction of upcoming actions. Each LLM model can be changed to a higher/pro version however, for testing we utilized a lower version of Gemini.

---

## Metrics and Results

| Metric                 | Value            | Description                                          |
| :--------------------- | :--------------- | :--------------------------------------------------- |
| Sequence Accuracy      | 100.00 %         | Detected vs ground-truth moves matching rate         |
| Average Latency        | 5206.58 ms/query | Gemini move-detection latency                        |
| Event MAE              | 0 moves          | Difference between detected and actual move count    |
| Stockfish Eval         | +0.5             | Slight advantage to White in final state             |
| Guardrail Success Rate | No Metric        | All illegal moves caught and re-routed by the coach  |

Metrics captured via Streamlit output (see screenshots in repo under Metrics & Evals folder).

---

## Example Temporal Reasoning Output

From `gemini_temporal_reasoning.py`:

1. Gemini Frame Comparison → Identified move e2-e4
2. Stockfish Query → Evaluation +0.4  Best move e7-e5
3. Gemini Prediction → d2-d4 (expected next move)
4. Temporal Accuracy → Ground truth d2-d4 match

The system therefore demonstrates temporal sequence comprehension across frames and can predict likely future actions.

---

## Integration and Reuse from Prior Modules

* GraphRAG structure: kept modular for future retrieval integration (Week 6 concepts).
* Agent architecture: commentator, coach, and opponent agents communicate as multi-step LLM orchestration (Weeks 7 – 8 speech & deployment).
* Evaluation logging: `game_file_logger.py` produces CSV entries for future ablation studies.
* Streamlit UI: visualizes game state, temporal predictions, and metrics in real time.

---

## Qualitative Observations

* Conversational coherence: LLM maintains awareness of move order and context throughout entire games.
* Learning feedback: Coach agent provides [INTERVENTION] feedback on mistakes and encouragement on sound moves.
* Temporal reasoning: Gemini successfully tracks turn-by-turn state and predicts next actions with low latency.
* Speech interface: Voice commands (“Pawn to E4”) function reliably; text-to-speech returns coach feedback audibly.

---

## Reflection

This track demonstrates temporal LLM reasoning in an interactive game context where each frame (board state) represents a temporal slice of action. Gemini handles multi-frame comparisons to infer moves and predict upcoming events, while Stockfish serves as ground-truth reference.

The combination of LLM reflection (coach), symbolic engine evaluation (Stockfish), and real-time UI forms a complete temporal reasoning loop with human-in-the-loop learning.

Ethically, the project uses self-generated data only — no personal images or third-party identifiers are stored or shared.

---

