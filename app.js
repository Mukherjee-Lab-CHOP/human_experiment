const CONFIG = Object.freeze({
  debugMode: false,
  blockCount: 9,
  practiceTrials: 5,
  practiceRewardProbability: 0.50,
  responseTimeoutSeconds: 3,
});

const BLOCK_PROBABILITIES = Object.freeze({
  H: Object.freeze({ high: 0.50, low: 0.50, label: '50/50' }),
  M: Object.freeze({ high: 0.65, low: 0.35, label: '65/35' }),
  L: Object.freeze({ high: 0.80, low: 0.20, label: '80/20' }),
});

// Generated once from a geometric distribution constrained to 30–150 trials
// with an expected mean of 60, then frozen for reproducible experiments.
const FIXED_SCHEDULES = Object.freeze([
  Object.freeze({ id: 'schedule_1', types: 'LHLMLLMLL', lengths: Object.freeze([45, 116, 54, 31, 36, 66, 78, 33, 81]) }),
  Object.freeze({ id: 'schedule_2', types: 'LMLLHLLML', lengths: Object.freeze([31, 42, 48, 103, 31, 120, 73, 59, 33]) }),
  Object.freeze({ id: 'schedule_3', types: 'LLMLLMLHL', lengths: Object.freeze([42, 37, 68, 34, 69, 117, 78, 42, 53]) }),
]);

const $ = (id) => document.getElementById(id);
const STIMULI = {
  APPLE: { src: 'assets/apple.png', label: 'Apple' },
  BANANA: { src: 'assets/banana.png', label: 'Banana' },
};

let state;
let trial;
let pendingRow;
let active = false;
let timer;
let started;
let sessionId;
let tutorialStage = 0;

function show(id) {
  ['instructions', 'task', 'complete'].forEach((name) =>
    $(name).classList.toggle('hidden', name !== id)
  );
}

function randomInteger(minimum, maximum) {
  return Math.floor(Math.random() * (maximum - minimum + 1)) + minimum;
}

function oppositeFruit(fruit) {
  return fruit === 'APPLE' ? 'BANANA' : 'APPLE';
}

function makeBlockSchedule() {
  const schedule = FIXED_SCHEDULES[randomInteger(0, FIXED_SCHEDULES.length - 1)];
  const blocks = [];
  let higherProbabilityFruit = Math.random() < 0.5 ? 'APPLE' : 'BANANA';
  for (let index = 0; index < schedule.types.length; index++) {
    const favoredSwitched = index > 0;
    if (favoredSwitched) higherProbabilityFruit = oppositeFruit(higherProbabilityFruit);
    const blockType = schedule.types[index];
    const probabilities = BLOCK_PROBABILITIES[blockType];
    blocks.push({
      number: index + 1,
      scheduleId: schedule.id,
      blockType,
      length: schedule.lengths[index],
      highProbability: probabilities.high,
      lowProbability: probabilities.low,
      favoredFruit: blockType === 'H' ? '' : higherProbabilityFruit,
      higherProbabilityFruit,
      favoredSwitched: index === 0 ? null : favoredSwitched,
    });
  }
  return blocks;
}

function queuedRewardProbability(baseProbability, skippedTrials) {
  // P(queue reward) = 1 - (1 - p)^(n + 1), calculated independently per fruit.
  // Once queued, a reward remains available until that fruit is selected.
  return 1 - Math.pow(1 - baseProbability, skippedTrials + 1);
}

function resetBaiting() {
  state.appleUnchosen = 0;
  state.bananaUnchosen = 0;
  state.appleBaited = false;
  state.bananaBaited = false;
}

function showTutorialStage(stage) {
  tutorialStage = stage;
  $('tutorialProgress').textContent = `${stage + 1} of 4`;
  const showProbabilities = stage >= 2;
  $('tutorialAppleProbability').classList.toggle('hidden', !showProbabilities);
  $('tutorialBananaProbability').classList.toggle('hidden', !showProbabilities);
  $('tutorialContinue').classList.toggle('hidden', stage !== 2);
  $('start').classList.toggle('hidden', stage !== 3);
  $('tutorialApple').disabled = stage >= 2;
  $('tutorialBanana').disabled = stage >= 2;

  if (stage === 0) {
    $('tutorialText').textContent = 'You’ll be given the option of an apple or a banana. Your goal is to collect as many gold coins as possible. Click either fruit to continue.';
  } else if (stage === 1) {
    $('tutorialText').textContent = 'One fruit will have a higher probability of giving a gold coin, and the other will have a lower probability. Click either fruit.';
  } else if (stage === 2) {
    $('tutorialText').textContent = 'Here were their probabilities of giving a gold coin.';
    $('tutorialAppleProbability').textContent = '80%';
    $('tutorialBananaProbability').textContent = '20%';
  } else {
    $('tutorialText').textContent = 'Periodically, the gold-coin probabilities may switch—including which fruit has the higher probability.';
    $('tutorialAppleProbability').textContent = '20%';
    $('tutorialBananaProbability').textContent = '80%';
  }
}

function chooseTutorialFruit() {
  if (tutorialStage < 2) showTutorialStage(tutorialStage + 1);
}

$('tutorialApple').onclick = chooseTutorialFruit;
$('tutorialBanana').onclick = chooseTutorialFruit;
$('tutorialContinue').onclick = () => showTutorialStage(3);
showTutorialStage(0);

$('start').onclick = async () => {
  try {
    const response = await fetch('/api/participant', { cache: 'no-store' });
    if (!response.ok) throw Error('Could not assign a participant ID');

    const participant = (await response.json()).participant_id;
    const blocks = makeBlockSchedule();
    state = {
      participant,
      phase: 'practice',
      practiceCompleted: 0,
      mainCompleted: 0,
      blockIndex: 0,
      blockCompleted: 0,
      score: 0,
      blocks,
      totalMainTrials: blocks.reduce((total, block) => total + block.length, 0),
    };
    resetBaiting();
    sessionId = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+/, '').replace('T', '_');
    show('task');
    beginTrial();
  } catch (error) {
    alert('The experiment could not start: ' + error.message);
  }
};

function setStimulus(buttonId, stimulus) {
  const button = $(buttonId);
  const image = button.querySelector('.stimulus');
  image.src = STIMULI[stimulus].src;
  image.alt = STIMULI[stimulus].label;
  button.setAttribute('aria-label', `Choose ${STIMULI[stimulus].label}`);
}

function beginTrial() {
  const isPractice = state.phase === 'practice';
  const currentBlock = isPractice ? null : state.blocks[state.blockIndex];
  const number = isPractice ? state.practiceCompleted + 1 : state.mainCompleted + 1;
  let appleProbability;
  let bananaProbability;
  let appleBaited;
  let bananaBaited;

  if (isPractice) {
    appleProbability = CONFIG.practiceRewardProbability;
    bananaProbability = CONFIG.practiceRewardProbability;
    appleBaited = Math.random() < appleProbability;
    bananaBaited = Math.random() < bananaProbability;
  } else {
    appleProbability = currentBlock.blockType === 'H' ? currentBlock.highProbability : currentBlock.favoredFruit === 'APPLE'
      ? currentBlock.highProbability
      : currentBlock.lowProbability;
    bananaProbability = currentBlock.blockType === 'H' ? currentBlock.highProbability : currentBlock.favoredFruit === 'BANANA'
      ? currentBlock.highProbability
      : currentBlock.lowProbability;
    if (!state.appleBaited) {
      state.appleBaited = Math.random() < queuedRewardProbability(appleProbability, state.appleUnchosen);
    }
    if (!state.bananaBaited) {
      state.bananaBaited = Math.random() < queuedRewardProbability(bananaProbability, state.bananaUnchosen);
    }
    appleBaited = state.appleBaited;
    bananaBaited = state.bananaBaited;
  }

  const flip = Math.random() < 0.5;
  trial = {
    phase: state.phase,
    number,
    blockNumber: currentBlock?.number ?? '',
    blockTrialNumber: isPractice ? '' : state.blockCompleted + 1,
    blockLength: currentBlock?.length ?? '',
    scheduleId: currentBlock?.scheduleId ?? '',
    blockType: currentBlock?.blockType ?? '',
    probabilityCondition: isPractice ? '50/50 practice' : BLOCK_PROBABILITIES[currentBlock.blockType].label,
    favoredFruit: currentBlock?.favoredFruit ?? '',
    favoredSwitched: currentBlock?.favoredSwitched ?? '',
    left: flip ? 'APPLE' : 'BANANA',
    right: flip ? 'BANANA' : 'APPLE',
    appleProbability,
    bananaProbability,
    appleUnchosen: state.appleUnchosen,
    bananaUnchosen: state.bananaUnchosen,
    appleBaited,
    bananaBaited,
  };

  pendingRow = null;
  setStimulus('left', trial.left);
  setStimulus('right', trial.right);
  $('progress').textContent = isPractice
    ? `Practice ${number} of ${CONFIG.practiceTrials}`
    : `Block ${currentBlock.number} of ${CONFIG.blockCount} • Trial ${trial.blockTrialNumber} of ${currentBlock.length}`;
  $('progress').classList.toggle('hidden', !CONFIG.debugMode);
  updateExperimentProgress();
  $('score').classList.toggle('hidden', isPractice);
  $('scoreValue').textContent = state.score;
  $('prompt').textContent = isPractice ? 'Practice: choose one' : 'Choose one';
  $('feedback').classList.add('hidden');
  $('left').className = 'option';
  $('right').className = 'option';
  $('left').disabled = false;
  $('right').disabled = false;
  active = true;
  started = performance.now();
  timer = setTimeout(() => respond('TIMEOUT'), CONFIG.responseTimeoutSeconds * 1000);
}

function updateExperimentProgress() {
  const completed = state.practiceCompleted + state.mainCompleted;
  const total = CONFIG.practiceTrials + state.totalMainTrials;
  const percentage = total > 0 ? (completed / total) * 100 : 0;
  $('experimentProgressBar').style.width = `${percentage}%`;
  $('experimentProgress').setAttribute('aria-valuenow', String(Math.round(percentage)));
}

function respond(side) {
  if (!active) return;
  const responseRecordedAt = new Date().toISOString();
  active = false;
  clearTimeout(timer);
  $('left').disabled = true;
  $('right').disabled = true;

  let choice = '';
  let rewarded = false;
  let reactionTime = '';
  let choiceClickedAt = '';

  if (side !== 'TIMEOUT') {
    choiceClickedAt = responseRecordedAt;
    reactionTime = Math.round(performance.now() - started);
    choice = side === 'LEFT' ? trial.left : trial.right;
    rewarded = choice === 'APPLE' ? trial.appleBaited : trial.bananaBaited;

    if (trial.phase === 'main') {
      if (rewarded) {
        if (choice === 'APPLE') state.appleBaited = false;
        else state.bananaBaited = false;
      }
      if (choice === 'APPLE') {
        state.appleUnchosen = 0;
        state.bananaUnchosen++;
      } else {
        state.bananaUnchosen = 0;
        state.appleUnchosen++;
      }
    }
    if (rewarded && trial.phase === 'main') state.score++;
  }

  if (trial.phase === 'practice') state.practiceCompleted++;
  else {
    state.mainCompleted++;
    state.blockCompleted++;
  }
  updateExperimentProgress();

  pendingRow = {
    participant_id: state.participant,
    session_id: sessionId,
    phase: trial.phase,
    trial_number: trial.number,
    block_number: trial.blockNumber,
    block_trial_number: trial.blockTrialNumber,
    block_length: trial.blockLength,
    total_scheduled_main_trials: state.totalMainTrials,
    schedule_id: trial.scheduleId,
    block_type: trial.blockType,
    probability_condition: trial.probabilityCondition,
    favored_fruit: trial.favoredFruit,
    favored_fruit_switched: trial.favoredSwitched === '' ? '' : Number(trial.favoredSwitched),
    left_stimulus: trial.left,
    right_stimulus: trial.right,
    apple_base_probability: trial.appleProbability,
    banana_base_probability: trial.bananaProbability,
    apple_unchosen_before: trial.appleUnchosen,
    banana_unchosen_before: trial.bananaUnchosen,
    apple_baited: Number(trial.appleBaited),
    banana_baited: Number(trial.bananaBaited),
    choice_side: side,
    chosen_stimulus: choice,
    choice_clicked_at: choiceClickedAt,
    response_recorded_at: responseRecordedAt,
    next_clicked_at: '',
    reaction_time_ms: reactionTime,
    reward: Number(rewarded),
    cumulative_score: state.score,
    saved_at: '',
  };

  if (side !== 'TIMEOUT') $(side.toLowerCase()).classList.add(rewarded ? 'rewarded' : 'not-rewarded');
  $('score').classList.toggle('hidden', trial.phase === 'practice');
  $('scoreValue').textContent = state.score;
  $('coinReward').classList.toggle('hidden', !rewarded);
  $('feedbackText').textContent = side === 'TIMEOUT' ? 'No gold coin — time ran out' : rewarded ? 'Gold coin!' : 'No gold coin';
  $('feedbackText').className = rewarded ? 'status-ok' : 'status-bad';
  $('nextTrial').textContent = nextActionLabel();
  $('nextTrial').disabled = false;
  $('feedback').classList.remove('hidden');
  $('nextTrial').focus();
}

function nextActionLabel() {
  if (trial.phase === 'practice' && state.practiceCompleted >= CONFIG.practiceTrials) return 'Begin experiment';
  if (trial.phase === 'main' && state.mainCompleted >= state.totalMainTrials) return 'Finish';
  return 'Next trial';
}

async function savePendingTrial() {
  pendingRow.saved_at = new Date().toISOString();
  const response = await fetch('/api/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(pendingRow),
  });
  if (!response.ok) throw Error((await response.json()).error || 'Save failed');
}

$('nextTrial').onclick = async () => {
  if (!pendingRow) return;
  $('nextTrial').disabled = true;
  if (!pendingRow.next_clicked_at) pendingRow.next_clicked_at = new Date().toISOString();

  try {
    await savePendingTrial();
    $('saveError').textContent = '';
  } catch (error) {
    $('saveError').textContent = 'Could not save this trial: ' + error.message;
    $('nextTrial').disabled = false;
    return;
  }

  if (trial.phase === 'practice' && state.practiceCompleted >= CONFIG.practiceTrials) {
    state.phase = 'main';
    state.blockIndex = 0;
    state.blockCompleted = 0;
    resetBaiting();
    beginTrial();
  } else if (trial.phase === 'main' && state.mainCompleted >= state.totalMainTrials) {
    $('finalScore').textContent = `You earned ${state.score} gold coins.`;
    show('complete');
  } else {
    const finishedBlock = trial.phase === 'main'
      && state.blockCompleted >= state.blocks[state.blockIndex].length;
    if (finishedBlock) {
      state.blockIndex++;
      state.blockCompleted = 0;
      resetBaiting();
    }
    beginTrial();
  }
};

$('left').onclick = () => respond('LEFT');
$('right').onclick = () => respond('RIGHT');
