const assert = require('node:assert/strict');
const {test} = require('node:test');
const select = require('./select-pr.cjs');

function fixture() {
  const repository = {
    full_name: 'dlobato/drydock', default_branch: 'main',
    owner: {login: 'dlobato', id: 1379455},
  };
  const commit = 'a'.repeat(40);
  const context = {
    eventName: 'workflow_dispatch', actor: 'collaborator',
    repo: {owner: 'dlobato', repo: 'drydock'},
    ref: 'refs/heads/main', sha: 'b'.repeat(40),
    payload: {inputs: {pull_request: '18'}},
  };
  const env = {
    GITHUB_TRIGGERING_ACTOR: 'collaborator',
    GITHUB_WORKFLOW_REF: 'dlobato/drydock/.github/workflows/pre-deployment.yml@refs/heads/main',
    GITHUB_WORKFLOW_SHA: context.sha, GITHUB_RUN_ID: '100', GITHUB_RUN_ATTEMPT: '1',
  };
  const protection = {protected: true};
  const headCommit = {commit: {message: 'Update fabric [digital-twin-test]'}};
  const pr = {
    number: 18, state: 'open',
    base: {repo: {full_name: repository.full_name}, ref: 'main'},
    head: {repo: {full_name: repository.full_name}, sha: commit},
  };
  const calls = [];
  const response = (name, data) => async (args) => {
    calls.push([name, args]);
    return {data};
  };
  const github = {rest: {
    repos: {get: response('repository', repository), getBranch: response('branch', protection), getCommit: response('commit', headCommit)},
    pulls: {get: response('pr', pr)},
  }};
  return {github, context, env, repository, protection, pr, headCommit, calls};
}

test('any dispatch actor can select an immutable PR commit before native approval', async () => {
  const f = fixture();
  const result = await select(f);
  assert.deepEqual(result, {
    repository: 'dlobato/drydock', pull_request: 18, commit: 'a'.repeat(40),
    workflow_commit: 'b'.repeat(40), run: '100', attempt: '1',
  });
  assert.deepEqual(f.calls, [
    ['repository', {owner: 'dlobato', repo: 'drydock'}],
    ['branch', {owner: 'dlobato', repo: 'drydock', branch: 'main'}],
    ['pr', {owner: 'dlobato', repo: 'drydock', pull_number: 18}],
  ]);
  f.env.GITHUB_RUN_ATTEMPT = '2';
  assert.equal((await select(f)).attempt, '2');
  f.pr.head.sha = 'c'.repeat(40);
  assert.equal(result.commit, 'a'.repeat(40));
  assert.equal((await select(f)).commit, 'c'.repeat(40));
});

for (const [name, change] of [
  ['push event', f => { f.context.eventName = 'push'; }],
  ['missing input', f => { delete f.context.payload.inputs; }],
  ['invalid PR number', f => { f.context.payload.inputs.pull_request = '../18'; }],
  ['inexact PR number', f => { f.context.payload.inputs.pull_request = '9007199254740993'; }],
  ['fork repository', f => { f.repository.full_name = 'fork/drydock'; }],
  ['PR workflow branch', f => { f.context.ref = 'refs/heads/feature'; }],
  ['untrusted workflow ref', f => { f.env.GITHUB_WORKFLOW_REF = 'dlobato/drydock/.github/workflows/pre-deployment.yml@refs/heads/feature'; }],
  ['another workflow', f => { f.env.GITHUB_WORKFLOW_REF = 'dlobato/drydock/.github/workflows/other.yml@refs/heads/main'; }],
  ['workflow commit mismatch', f => { f.env.GITHUB_WORKFLOW_SHA = 'c'.repeat(40); }],
  ['unprotected default branch', f => { f.protection.protected = false; }],
  ['closed PR', f => { f.pr.state = 'closed'; }],
  ['fork PR', f => { f.pr.head.repo.full_name = 'fork/drydock'; }],
  ['deleted PR repository', f => { f.pr.head.repo = null; }],
  ['another base repository', f => { f.pr.base.repo.full_name = 'fork/drydock'; }],
  ['another base branch', f => { f.pr.base.ref = 'release'; }],
  ['invalid head commit', f => { f.pr.head.sha = 'main'; }],
]) {
  test(`reject ${name}`, async () => {
    const f = fixture();
    change(f);
    await assert.rejects(select(f));
  });
}

test('API failure stops selection before approval', async () => {
  const f = fixture();
  f.github.rest.repos.getBranch = async () => { throw new Error('API unavailable'); };
  await assert.rejects(select(f), /API unavailable/);
  assert.equal(f.calls.some(([name]) => name === 'pr'), false);
});

function markerFixture() {
  const f = fixture();
  f.context.eventName = 'pull_request_target';
  f.context.payload = {number: 18, pull_request: structuredClone(f.pr)};
  return f;
}

test('the marker requests approval for the exact PR event commit using trusted code', async () => {
  const f = markerFixture();
  const result = await select(f);
  assert.equal(result.commit, f.context.payload.pull_request.head.sha);
  assert.deepEqual(f.calls.at(-1), ['commit', {
    owner: 'dlobato', repo: 'drydock', ref: 'a'.repeat(40),
  }]);
  f.pr.head.sha = 'c'.repeat(40);
  assert.equal(result.commit, 'a'.repeat(40));
  assert.equal(await select(f), null);
});

for (const [name, change] of [
  ['no marker', f => { f.headCommit.commit.message = 'Update fabric'; }],
  ['different marker', f => { f.headCommit.commit.message = 'Update [test gke]'; }],
  ['different case', f => { f.headCommit.commit.message = '[DIGITAL-TWIN-TEST]'; }],
  ['incomplete marker', f => { f.headCommit.commit.message = '[digital-twin-test'; }],
  ['stale PR event', f => { f.pr.head.sha = 'c'.repeat(40); }],
  ['missing event commit', f => { delete f.context.payload.pull_request; }],
  ['fork PR', f => { f.pr.head.repo.full_name = 'fork/drydock'; }],
  ['deleted fork', f => { f.pr.head.repo = null; }],
  ['closed PR', f => { f.pr.state = 'closed'; }],
  ['different base', f => { f.pr.base.ref = 'release'; }],
]) {
  test(`PR event does not request approval: ${name}`, async () => {
    const f = markerFixture();
    change(f);
    assert.equal(await select(f), null);
  });
}

test('a marker in the head commit body also requests approval', async () => {
  const f = markerFixture();
  f.headCommit.commit.message = 'Update fabric\n\n[digital-twin-test]';
  assert.equal((await select(f)).commit, f.pr.head.sha);
});

test('a new head without the marker does not inherit an earlier request', async () => {
  const f = markerFixture();
  const previous = await select(f);
  f.pr.head.sha = 'c'.repeat(40);
  f.context.payload.pull_request = structuredClone(f.pr);
  f.headCommit.commit.message = 'Another change';
  assert.equal(await select(f), null);
  assert.equal(previous.commit, 'a'.repeat(40));
});

test('commit lookup failure cannot request approval', async () => {
  const f = markerFixture();
  f.github.rest.repos.getCommit = async () => { throw new Error('API unavailable'); };
  await assert.rejects(select(f), /API unavailable/);
});
