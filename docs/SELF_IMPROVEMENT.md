# Self-Improvement Guide — THE EYE

## Overview
THE EYE improves its prediction accuracy over time by tracking the outcomes of past predictions and adjusting its scoring models. This document explains the self-improvement mechanisms.

---

## How THE EYE Learns

### 1. Prediction Tracking
Every prediction is stored in `src/data/predictions.json` with:
- The original 7-field structured prediction
- Timestamp of prediction
- Token address
- Predicted event and timing
- Confidence level at prediction time

### 2. Outcome Validation
Periodically (via cleanup cron job), the system checks past predictions against actual outcomes:
- **Rug pull predicted**: Did the token actually rug? (Check liquidity, price)
- **Pump predicted**: Did the price sustain or dump?
- **Whale accumulation**: Did price increase after whale buys?
- **Temporal window**: Did the predicted event occur in the predicted window?

### 3. Accuracy Calculation
For each agent and pattern type:
```
accuracy = correct_predictions / total_predictions
```
Where a prediction is "correct" if:
- The predicted event occurred
- The timing was within the predicted window (or ±50% of estimated time)
- The direction (bullish/bearish) was correct

### 4. Weight Adjustment
Based on accuracy, the scoring model weights are adjusted:
- **Agent weight**: Agents with higher accuracy get more weight in conflict resolution
- **Factor weight**: Risk factors that correctly predicted outcomes get increased weight
- **Pattern weight**: Patterns with higher hit rates are prioritized

---

## Scoring Model Evolution

### Initial Weights (Rug Pull Probability)
```
contract_risk:     0.30
liquidity_risk:    0.25
distribution_risk: 0.20
developer_risk:    0.15
pattern_risk:      0.10
```

### After 100+ Validated Predictions
Weights shift based on what actually predicted rugs:
- If `developer_risk` was present in 80% of actual rugs → weight increases
- If `distribution_risk` was rarely present in actual rugs → weight decreases
- Total weights always sum to 1.0

### Adjustment Formula
```
new_weight = old_weight + (accuracy - 0.5) * learning_rate
```
- `learning_rate`: 0.05 (conservative, prevents overfitting)
- Weights normalized to sum to 1.0 after adjustment
- Minimum weight: 0.05 (no factor is ever completely ignored)

---

## Agent Confidence Calibration

### Problem
Agents may be overconfident or underconfident. An agent that says "confidence: 0.9" but is only right 50% of the time is overconfident.

### Solution
Track each agent's historical accuracy and apply calibration:
```
calibrated_confidence = raw_confidence * (agent_accuracy / average_accuracy)
```

### Example
- Agent A: raw_confidence 0.8, historical accuracy 70%
- Agent B: raw_confidence 0.7, historical accuracy 85%
- Average accuracy: 77.5%
- Agent A calibrated: 0.8 * (0.70 / 0.775) = 0.72
- Agent B calibrated: 0.7 * (0.85 / 0.775) = 0.77

After calibration, Agent B's prediction gets more weight despite lower raw confidence.

---

## Pattern Frequency Analysis

### Learning New Patterns
Over time, the system may discover new patterns:
1. Track all features of tokens that rugged
2. Identify common features across rugged tokens
3. If a feature appears in >60% of rugs but <30% of non-rugs → potential new pattern
4. Add to pattern catalog with initial confidence 0.3
5. Validate against future predictions
6. If accuracy >60% over 20+ predictions → promote to official pattern

### Pattern Retirement
Patterns that fall below 40% accuracy over 50+ predictions are:
- Flagged as "deprecated"
- Weight reduced to 0.05
- Not removed (may become accurate again in different market conditions)

---

## Whale Accuracy Tracking

### Per-Whale Scoring
Each whale wallet in `whale_db.json` has an accuracy score:
- Track every whale trade the system observed
- Did the token price increase after whale buy? (within 24h, 48h, 7d)
- Accuracy = profitable_trades / total_trades

### Usage in Predictions
- Whale with >70% accuracy: confidence bonus +0.15
- Whale with >85% accuracy: confidence bonus +0.25, tagged as "alpha_whale"
- Whale with <30% accuracy: confidence penalty -0.10, tagged as "noisy_whale"
- Whale with <10% accuracy: ignored in predictions

---

## Temporal Pattern Learning

### Historical Timing Analysis
The system learns when events are most likely to occur:
- Record timestamps of all rug pulls, dumps, and organic pumps
- Analyze hour-of-day distribution
- Analyze day-of-week distribution
- Analyze time-since-token-creation distribution
- Update temporal risk windows based on accumulated data

### Example Learning
```
After 50 rug pulls observed:
- 02:00-06:00 UTC: 35 rugs (70%) → high risk window
- 14:00-18:00 UTC: 5 rugs (10%) → low risk window
- <24h old: 30 rugs (60%) → very high risk
- 24h-7d old: 15 rugs (30%) → moderate risk
- >7d old: 5 rugs (10%) → lower risk
```

---

## Self-Improvement Cycle

### Weekly (via cleanup cron)
1. Validate all predictions older than 7 days
2. Calculate accuracy for each agent, pattern, and whale
3. Adjust scoring weights based on accuracy
4. Calibrate confidence levels
5. Identify potential new patterns
6. Retire underperforming patterns
7. Update temporal risk distributions
8. Save updated weights to `src/data/model_weights.json`

### Monthly
1. Full model retraining (recalculate all weights from scratch)
2. Pattern catalog review
3. Whale accuracy leaderboard update
4. Generate accuracy report

---

## Accuracy Metrics

### Key Metrics Tracked
- **Overall Accuracy**: % of predictions that were correct
- **Rug Detection Rate**: % of actual rugs that were predicted
- **False Alarm Rate**: % of rug predictions where no rug occurred
- **Timing Accuracy**: % of predictions where timing was within ±50%
- **Directional Accuracy**: % of predictions where direction was correct
- **Per-Agent Accuracy**: Accuracy broken down by each agent
- **Per-Pattern Accuracy**: Accuracy broken down by each pattern

### Target Accuracy
- Rug detection: >70% (missing rugs is worse than false alarms)
- Directional accuracy: >60%
- Timing accuracy: >50%
- Overall: >65% (significantly better than random)

---

## Data Requirements for Learning

### Minimum Data Points
- **Weight adjustment**: 20 validated predictions per factor
- **New pattern discovery**: 50+ validated observations
- **Confidence calibration**: 30+ predictions per agent
- **Temporal patterns**: 30+ events of same type
- **Whale accuracy**: 10+ observed trades per whale

### Cold Start
When the system has no historical data:
1. Use default weights (evenly distributed)
2. Use industry-standard heuristics (70% rugs in ghost hours, etc.)
3. Confidence starts at 0.5 for all predictions
4. Learning begins after first 20 predictions are validated

---

## Configuration

### Learning Parameters (in model_weights.json)
```json
{
  "learning_rate": 0.05,
  "min_weight": 0.05,
  "validation_window_days": 7,
  "calibration_enabled": true,
  "pattern_discovery_enabled": true,
  "pattern_promotion_threshold": 0.60,
  "pattern_retirement_threshold": 0.40,
  "min_predictions_for_adjustment": 20
}
```
