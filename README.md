# Human Probability Reversal Experiment

A local browser-based apple-versus-banana choice task. It begins with 5 practice trials, followed by 10 independently randomized experimental blocks. Participants receive gold-coin feedback and must click **Next trial** after reviewing each result.

## Run

Requires Python 3. No external packages are needed.

Before the first run, open this project's Supabase SQL Editor and run the contents of `supabase/setup.sql`. This creates the `experiment_trials` table with Row Level Security, grants anonymous clients INSERT only, and intentionally provides no SELECT, UPDATE, or DELETE access.

```bash
python3 app.py
```

The experiment opens in your browser. Keep the launching terminal open so each trial can be saved. Participants click either fruit to make their choice. After **Next trial** is clicked, the browser sends the completed row only to the local Python backend. The backend validates it and writes it to Supabase.

Supabase settings are read from the local `.env` file, which is excluded from Git. Copy `.env.example` when configuring another computer. The Supabase URL and publishable key are never included in the browser JavaScript.

The local web server also blocks all `/data` URLs. Trial records and participant counters are not written locally; unique participant IDs are generated in memory, and the database has no anonymous read policy.

## Deploy to Vercel

The project is ready for Vercel's **Other** framework preset. The HTML, CSS, JavaScript, and images are static files. Vercel runs `api/participant.py` and `api/save.py` as temporary Python Functions, so no permanent Python server or custom port is required.

In Vercel's Build and Output Settings, leave the Build Command, Output Directory, and Install Command blank. Add these environment variables for Production, Preview, and Development:

```text
SUPABASE_URL=https://axusexbryxfjszklcjnv.supabase.co
SUPABASE_PUBLISHABLE_KEY=<your publishable key>
```

Do not add a frontend prefix to either variable. Redeploy after adding or changing environment variables. The local `.env` file is excluded from Git and Vercel uploads.

The browser calls `/api/participant` to obtain a unique ID and `/api/save` to submit completed trials. Only the Python function reads the Supabase environment variables.

## Change experiment settings

There is no participant-facing setup screen. All settings are at the top of `app.js` in the `CONFIG` object. Edit a number, save the file, and restart `app.py` before the next participant.

```js
const CONFIG = Object.freeze({
  debugMode: false,                // Show block/trial progress when true
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
- Every block boundary is a reversal: the fruit with the higher probability always switches. Block 1 randomly assigns the higher probability to apple or banana, and the favored fruit then alternates for every subsequent block.
- Bait and unchosen-trial counters reset at every block boundary.

During practice, apple and banana independently have a 50% chance of reward on each trial. Practice results are labeled with `phase` set to `practice`.

## Reward rule

Main trials queue rewards independently for apple and banana. An unbaited fruit is tested at the start of a trial using:

```text
1 - (1 - base_probability)^(unchosen_trials + 1)
```

Here, `p` is that fruit's block probability and `n` is the number of consecutive trials it was skipped before the current trial. Once a reward is queued, it persists until that fruit is chosen. Selecting the fruit consumes the queued reward and resets its skipped count; the other fruit's skipped count increases by one.

Block and trial counters are hidden from participants, while a number-free progress bar advances across practice and the full experiment. Set `debugMode` to `true` to display the counters during testing. Each choice trial times out after 3 seconds; after a timeout, the participant must click **Next trial** to continue.

## Saved timestamps and block data

Every Supabase row records the block number, within-block trial number, randomized block length, probability condition, favored fruit, and whether the favored fruit switched from the preceding block. It also records:

- `choice_clicked_at`: when the participant clicked apple or banana; blank after a timeout.
- `response_recorded_at`: when the choice or timeout was processed.
- `next_clicked_at`: when the participant clicked **Next trial**, **Begin experiment**, or **Finish**.
- `saved_at`: when the completed row was sent for saving.
- `reaction_time_ms`: elapsed time from presentation to the fruit choice.

## Validate

```bash
python3 -m unittest -v
```
