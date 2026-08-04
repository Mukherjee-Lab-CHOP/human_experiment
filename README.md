# Human Probability Reversal Experiment

A local browser-GUI version of the Shrew-HVScreen `choose_orientation` task. It uses the
same independently baited reward rule, randomizes horizontal/vertical stimuli
between left and right on every trial, and adds configurable probability-reversal
blocks. No animal hardware or external Python packages are required.

## Run

Requires Python 3. No external packages are needed.

```bash
python3 app.py
```

The experiment opens in your browser. Keep the launching terminal open while it
runs so each trial can be saved to CSV.

Participants choose left with **F** and right with **J**, or click either card.
Results are written after every trial to `data/<participant>_<timestamp>.csv`.
Participant IDs are assigned automatically and sequentially when a session starts.
The last assigned number is persisted in `data/.participant_sequence`.

## Experimental rule

An unbaited orientation is tested at the start of a trial using:

```text
1 - (1 - base_probability)^(unchosen_trials + 1)
```

Once baited, its reward persists until that orientation is chosen. Selecting an
orientation resets its unchosen counter and increments the other orientation's
counter. Timeouts leave both counters unchanged.

At each configured block boundary, the horizontal and vertical base probabilities
swap and bait/counter state is reset. Set **Reverse every N trials** to `0` to
reproduce the shrew code's no-automatic-reversal behavior.

## Validate the experiment engine

```bash
python3 -m unittest -v
```
