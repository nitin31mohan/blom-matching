## feature engineering
- embeddings-based representations
- preference vectors (learned from user taste profiles over time)
- recency-weighted activity


## Candidate generation
2 stages:
a. Recall: narrow down from MANY users to FEW potential matches (based on embedding similarity, shared interests, or regional proximity)
b. Filtering: Applying hard constraints (gender preferences, age range, mutual blocks, location radius)


## Ranking model
ranking models trained to optimise for,
X- probability of mutual liking
- long-term engagement (weighted match quality, message depth)
X- real-time signals (is other person online at time of like?)

