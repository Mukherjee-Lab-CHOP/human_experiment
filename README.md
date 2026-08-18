# Human Probability Reversal Experiment

A local browser-based apple-versus-banana choice task. It begins with 5 practice trials, followed by 10 independently randomized experimental blocks. Participants receive gold-coin feedback and must click **Next trial** after reviewing each result.

## Run

Requires Python 3. No external packages are needed.

```bash
python3 app.py
```

The experiment opens in your browser. Keep the launching terminal open so each trial can be saved to CSV. Participants click either fruit to make their choice. Results are written to `data/<participant>_<timestamp>.csv` after **Next trial** is clicked.

## Change experiment settings

There is no participant-facing setup screen. All settings are at the top of `app.js` in the `CONFIG` object. Edit a number, save the file, and restart `app.py` before the next participant.

```js
const CONFIG = Object.freeze({
  blockCount: 10,
  blockBaseTrials: 60,
  blockExtraTrialsMin: 1,
  blockExtraTrialsMax: 30,
  standardHighProbability: 0.80,
  standardLowProbability: 0.20,
  changedBlockChance: 0.10,       // Small per-block chance of 65/35
  minimumChangedBlocks: 2,        // Guarantee at least two 65/35 blocks
  changedHighProbability: 0.65,
  changedLowProbability: 0.35,
  favoredFruitSwitchChance: 0.50, // At each boundary: switch vs. stay
  practiceTrials: 5,
  practiceRewardProbability: 0.50,
  responseTimeoutSeconds: 20,
});
```

Probabilities use values from `0` to `1`; for example, `0.10` means 10%.

## Block schedule

Each participant receives a newly randomized 10-block schedule:

- Each block has 60 trials plus a random whole number from 1–30, giving 61–90 trials per block.
- Block 1 always uses an 80/20 probability spread. A 50/50 draw determines whether apple or banana is favored.
- Blocks 2–10 independently have a 10% chance of using 65/35 instead of 80/20.
- If random generation produces fewer than two 65/35 blocks, additional blocks are selected so the schedule always contains at least two.
- At each block boundary, there is an independent 50% chance that the favored fruit switches and a 50% chance it remains the same.
- Bait and unchosen-trial counters reset at every block boundary.

During practice, apple and banana independently have a 50% chance of reward on each trial. Practice results are labeled with `phase` set to `practice`.

## Reward rule

Main trials use independent baiting. An unbaited fruit is tested at the start of a trial using:

```text
1 - (1 - base_probability)^(unchosen_trials + 1)
```

Once baited, its reward persists until that fruit is chosen.

## Saved timestamps and block data

Every CSV row records the block number, within-block trial number, randomized block length, probability condition, favored fruit, and whether the favored fruit switched from the preceding block. It also records:

- `choice_clicked_at`: when the participant clicked apple or banana; blank after a timeout.
- `response_recorded_at`: when the choice or timeout was processed.
- `next_clicked_at`: when the participant clicked **Next trial**, **Begin experiment**, or **Finish**.
- `saved_at`: when the completed row was sent for saving.
- `reaction_time_ms`: elapsed time from presentation to the fruit choice.

## Validate

```bash
python3 -m unittest -v
```
