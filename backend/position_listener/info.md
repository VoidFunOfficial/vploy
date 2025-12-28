**Expert PolyMarket Market Evaluation Request:**

Please act as a seasoned PolyMarket analyst. Your task is to evaluate my initial assessment against the current market reality.

**Market Context:**
*   **Question:** [QUESTION]
*   **Rules:** [RULE]

**My Initial Assessment:**
*   **Predicted Outcome:** I am leaning towards **[SIDE]**
*   **My Probability:** I assign a **[OUR_PROBABILITY]%** probability to **[SIDE]** occurring.
*   **Supporting Arguments (for YES):**
[REASON_Y]
*   **Counter Arguments (for NO):**
[REASON_N]

**Current Market Situation:**
*   **Market Price:** The current price for [SIDE] is **[CURRENT_PRICE]**.
*   **Divergence:** This price is significantly different from my predicted probability of [OUR_PROBABILITY]%.

**Output Format:**
You must output the result strictly in valid JSON format. Do not include markdown code blocks (like ```json). Just the raw JSON string.

**JSON Schema:**
{
  "analysis_summary": {
    "primary_driver": "Choose one: 'HYPE' or 'REALITY'"
  },
  "new_reasons_yes": [...],
  "new_reasons_no": [...]
}
