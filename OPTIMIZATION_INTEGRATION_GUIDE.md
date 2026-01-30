# Integration Guide: Building the Optimization Model

## Overview
This document explains how to build the optimization algorithm in `part2_Optimization.ipynb` and integrate it with the Streamlit dashboard. Your optimization function will be called by `optimization_model.py`, which handles all dashboard integration.

---

## What Data You'll Receive

Your optimization function will receive these inputs from the dashboard:

### 1. **`team_df`** (pandas DataFrame)
- Pre-filtered to only players from the selected country
- Columns: `player_id`, `value_score`, `disability_score`, `country`

**Example:**
```
player_id | value_score | disability_score | country
player_1  | 8.5         | 2.0              | USA
player_2  | 7.2         | 3.5              | USA
player_3  | 9.1         | 1.5              | USA
```

### 2. **`availability`** (dict: player_id → bool)
- Which players are available for selection
- `True` = can select, `False` = unavailable
- Dashboard users control this via **checkboxes** in the left panel

**Example:**
```python
{
    "player_1": True,
    "player_2": False,
    "player_3": True
}
```

### 3. **`fatigue`** (dict: player_id → float, 0-100)
- Current fatigue level for each player
- 0 = fresh, 100 = exhausted
- Used to adjust player scores: `adjusted_score = value_score - fatigue_weight * (fatigue / 100)`
- Dashboard users control this via **sliders** in the left panel

**Example:**
```python
{
    "player_1": 30.0,  # Somewhat fresh
    "player_2": 75.0,  # Very tired
    "player_3": 10.0   # Fresh
}
```

### 4. **`disability_cap`** (float)
- Maximum total disability score allowed in the lineup
- **HARD CONSTRAINT** — cannot be violated
- Dashboard users control this via **number input** in the top bar

**Example:**
- `disability_cap = 8.0` means selected players' disability scores must sum to ≤ 8.0

### 5. **`fatigue_weight`** (float, default=2.0)
- How much fatigue penalizes the score
- Higher value = fatigue matters more
- Can be tuned based on sport requirements

### 6. **`lineup_size`** (int, default=4)
- Number of players to select for the lineup
- Currently fixed at 4, but designed to be flexible

---

## Required Output Format

Your optimization function must return a **dictionary** with this exact structure:

```python
{
    "lineup": ["player_1", "player_3", "player_5", "player_7"],  # List of selected player_ids
    "objective": 24.5,                                             # Total optimized score
    "disability_sum": 7.8,                                         # Total disability of selected players
    "notes": "Description of how optimization worked",             # Human-readable explanation
    "breakdown": [
        {
            "player_id": "player_1",
            "value_score": 8.5,
            "fatigue": 30.0,
            "adjusted_score": 7.4,
            "disability_score": 2.0
        },
        {
            "player_id": "player_3",
            "value_score": 9.1,
            "fatigue": 10.0,
            "adjusted_score": 8.9,
            "disability_score": 1.5
        },
        # ... repeat for each player in lineup
    ]
}
```

### Output Requirements:
- **`lineup`**: List must have exactly `lineup_size` players
- **`objective`**: Sum of `adjusted_score` for all selected players
- **`disability_sum`**: Sum of `disability_score` for all selected players (must be ≤ `disability_cap`)
- **`notes`**: String describing the optimization approach or result
- **`breakdown`**: Array with details for each selected player (helps dashboard explain choices)

---

## Step 1: Write Your Optimization Function

Create a function with this signature in `part2_Optimization.ipynb`:

```python
from typing import Dict, List
import pandas as pd

def optimize_lineup(
    team_df: pd.DataFrame,
    availability: Dict[str, bool],
    fatigue: Dict[str, float],
    disability_cap: float,
    fatigue_weight: float = 2.0,
    lineup_size: int = 4,
) -> Dict:
    """
    Optimize team lineup based on player scores and constraints.
    
    Args:
        team_df: DataFrame with columns [player_id, value_score, disability_score, country]
        availability: Dict mapping player_id to True/False
        fatigue: Dict mapping player_id to fatigue level (0-100)
        disability_cap: Maximum total disability score allowed (HARD CONSTRAINT)
        fatigue_weight: Penalty multiplier for fatigue (default 2.0)
        lineup_size: Number of players to select (default 4)
    
    Returns:
        Dict with keys: lineup, objective, disability_sum, notes, breakdown
        
    Example:
        >>> result = optimize_lineup(
        ...     team_df=players_df,
        ...     availability={"p1": True, "p2": False},
        ...     fatigue={"p1": 30.0, "p2": 50.0},
        ...     disability_cap=8.0
        ... )
        >>> result["lineup"]
        ['p1', 'p3', 'p5', 'p7']
    """
    # Your optimization logic here
    pass
```

---

## Step 2: Integration with Dashboard

### Option A: Direct Integration (Recommended)
Add your function directly to `optimization_model.py`:

1. Open `optimization_model.py`
2. Locate the `LineupOptimizer` class
3. Replace the `optimize_lineup()` method with your implementation
4. The dashboard will automatically use it

### Option B: Keep in Notebook
If you prefer to keep the function in `part2_Optimization.ipynb`:

1. Write your function in the notebook
2. Export it: `from part2_Optimization import optimize_lineup`
3. Add this import to `optimization_model.py`

---

## Step 3: Testing with Sample Data

Test your function before integrating:

```python
import pandas as pd

# Load ML scores from part1
player_scores = pd.read_excel('player_scores.xlsx')

# Create test inputs
team_df = player_scores[player_scores['country'] == 'USA'].head(10)
availability = {pid: True for pid in team_df['player_id']}
fatigue = {pid: 50.0 for pid in team_df['player_id']}
disability_cap = 8.0

# Call your function
result = optimize_lineup(
    team_df=team_df,
    availability=availability,
    fatigue=fatigue,
    disability_cap=disability_cap
)

# Verify output
print(f"Selected players: {result['lineup']}")
print(f"Optimization score: {result['objective']}")
print(f"Total disability: {result['disability_sum']} / {disability_cap}")
print(f"Is feasible: {result['disability_sum'] <= disability_cap}")
print(f"Breakdown:\n{pd.DataFrame(result['breakdown'])}")
```

**Checklist:**
- [ ] Lineup has exactly 4 players
- [ ] All players in `lineup` are available
- [ ] Total disability ≤ `disability_cap`
- [ ] `objective` = sum of adjusted scores
- [ ] `breakdown` has entry for each player in lineup
- [ ] Output can be returned when no feasible solution exists

---

## Step 4: End-to-End Testing

Once integrated, test the full dashboard flow:

```bash
# Make sure player_scores.xlsx exists (from part1)
streamlit run app.py
```

**Test scenarios in the dashboard:**
1. Adjust fatigue sliders — does optimization change?
2. Disable a high-scoring player — does it select others?
3. Lower disability cap — can it find a feasible lineup?
4. Check "Breakdown" to verify player selection logic

---

## Optimization Approaches

You can implement any algorithm. Here are some options:

### Brute Force (Good for 4-player lineups)
Try all combinations, pick best feasible one:
```python
from itertools import combinations

for combo in combinations(available_players, lineup_size):
    if sum(disability) <= disability_cap:
        # Calculate adjusted score and track best
```

### Greedy (Fast, simple)
Sort by adjusted score, add players until disability cap:
```python
sorted_players = team_df.sort_values('adjusted_score', ascending=False)
for player in sorted_players:
    if available and current_disability + player_disability <= disability_cap:
        lineup.append(player)
```

### Linear Programming (Optimal, scalable)
Use `scipy.optimize.linprog` or `PuLP`:
```python
from scipy.optimize import linprog

# Maximize: sum of adjusted_scores
# Subject to: sum of disability_scores <= disability_cap
# Variables: binary (player in lineup or not)
```

### Genetic Algorithm (For complex constraints)
Evolutionary approach for larger problems.

### Dynamic Programming
For specific problem structures.

**The dashboard doesn't care which method you use!** Only the output format matters.

---

## Common Edge Cases

### No Available Players
```python
if len(team_df[team_df['player_id'].isin(available_ids)]) < lineup_size:
    return {
        "lineup": [],
        "objective": 0.0,
        "disability_sum": 0.0,
        "notes": "Not enough available players",
        "breakdown": []
    }
```

### No Feasible Lineup (All combinations violate disability_cap)
```python
return {
    "lineup": [],
    "objective": 0.0,
    "disability_sum": 0.0,
    "notes": f"No feasible lineup under disability cap {disability_cap}",
    "breakdown": []
}
```

### All Players Equally Good
Return any valid lineup (dashboard will show the one chosen).

---

## Debugging Tips

1. **Print intermediate values:**
   ```python
   print(f"Available players: {len(available_df)}")
   print(f"Adjusted scores: {adjusted_df[['player_id', 'adjusted_score']]}")
   ```

2. **Verify constraint:**
   ```python
   assert result['disability_sum'] <= disability_cap, \
       f"Constraint violated: {result['disability_sum']} > {disability_cap}"
   ```

3. **Check breakdown matches lineup:**
   ```python
   assert len(result['breakdown']) == len(result['lineup'])
   assert set(r['player_id'] for r in result['breakdown']) == set(result['lineup'])
   ```

4. **Validate objective calculation:**
   ```python
   expected_objective = sum(r['adjusted_score'] for r in result['breakdown'])
   assert abs(result['objective'] - expected_objective) < 0.01
   ```

---

## Questions to Answer

Before submitting, verify:

- ✅ Does my lineup have exactly `lineup_size` players?
- ✅ Are all players in `lineup` in the `availability` dict?
- ✅ Is total disability ≤ `disability_cap`?
- ✅ Is `objective` = sum of adjusted_scores?
- ✅ Does `breakdown` have entry for each player in lineup?
- ✅ Does my function handle edge cases (no players, no feasible solution)?
- ✅ What happens if fatigue weight changes?
- ✅ How does my algorithm scale if lineup_size increases?

---

## Questions? 

Check the function signature in `optimization_model.py` if you have questions about the expected inputs/outputs!
