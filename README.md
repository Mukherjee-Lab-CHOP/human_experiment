# Human Probability Reversal Experiment

A local browser-based apple-versus-banana choice task. It begins with 5 practice trials, followed by one of three fixed 9-block schedules. Participants receive gold-coin feedback and must click **Next trial** after reviewing each result.

## Run

Requires Python 3. No external packages are needed.

For an existing database, open the Supabase SQL Editor and run `supabase/add_fixed_schedule_fields.sql` once before deploying this version. It adds the fixed-schedule metadata fields used by new trial records.

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
  blockCount: 9,
  practiceTrials: 5,
  practiceRewardProbability: 0.50,
  responseTimeoutSeconds: 3,
});
```

The fixed schedule definitions and their block lengths are immediately below `CONFIG` in `app.js`. Probabilities use values from `0` to `1`; for example, `0.20` means 20%.

## Block schedule

Each participant is assigned uniformly at random to one of three fixed schedules:

| Schedule | Block types | Fixed trial lengths |
| --- | --- | --- |
| `schedule_1` | `LHLMLLMLL` | 45, 116, 54, 31, 36, 66, 78, 33, 81 |
| `schedule_2` | `LMLLHLLML` | 31, 42, 48, 103, 31, 120, 73, 59, 33 |
| `schedule_3` | `LLMLLMLHL` | 42, 37, 68, 34, 69, 117, 78, 42, 53 |

`H` is 50/50, `M` is 65/35, and `L` is 80/20. Every schedule therefore contains one H block, two M blocks, and six L blocks. The lengths were drawn once from a capped geometric distribution with a minimum of 30, an expected mean of 60, and a maximum of 150 trials. Each listed schedule has an actual mean block length of 60 trials.

- Every block boundary is a reversal. The initially higher-probability fruit is randomized, then alternates at every subsequent block. An H block has no favored fruit, but the alternation continues through it for the following unequal block.
- Bait and unchosen-trial counters reset at every block boundary.

During practice, apple and banana independently have a 50% chance of reward on each trial. Practice results are labeled with `phase` set to `practice`.

## Reward rule

Main trials queue rewards independently for apple and banana. An unbaited fruit is tested at the start of a trial using:

```text
1 - (1 - base_probability)^(unchosen_trials + 1)
```

Here, `p` is that fruit's block probability and `n` is the number of consecutive completed choices for which it was skipped before the current trial. Both fruits are evaluated independently on every trial when they do not already have a queued reward. Once a reward is queued, it persists until that fruit is chosen. Selecting the fruit consumes its queued reward and resets its skipped count; the other fruit's skipped count increases by one. A timeout is treated as an omission: neither skipped count nor either fruit's queued-reward state changes.

Block and trial counters are hidden from participants, while a number-free progress bar advances across practice and the full experiment. Set `debugMode` to `true` to display the counters during testing. Each choice trial times out after 3 seconds; after a timeout, the participant must click **Next trial** to continue.

## Saved timestamps and block data

Every Supabase row records the assigned `schedule_id`, block type, block number, within-block trial number, fixed block length, probability condition, favored fruit, and whether the favored fruit switched from the preceding block. It also records:

- `choice_clicked_at`: when the participant clicked apple or banana; blank after a timeout.
- `response_recorded_at`: when the choice or timeout was processed.
- `next_clicked_at`: when the participant clicked **Next trial**, **Begin experiment**, or **Finish**.
- `saved_at`: when the completed row was sent for saving.
- `reaction_time_ms`: elapsed time from presentation to the fruit choice.

## Validate

```bash
python3 -m unittest -v
```
