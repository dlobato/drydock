module.exports = async function select({github, context, env}) {
  const fromPR = context.eventName === 'pull_request_target';
  const input = fromPR ? String(context.payload.number ?? '') : context.payload.inputs?.pull_request ?? '';
  if ((!fromPR && context.eventName !== 'workflow_dispatch') ||
      !/^[1-9][0-9]*$/.test(input) || !Number.isSafeInteger(Number(input))) {
    throw new Error('Select a PR through manual dispatch or a trusted PR event.');
  }

  const {data: repository} = await github.rest.repos.get(context.repo);
  const branch = repository.default_branch;
  if (repository.full_name !== 'dlobato/drydock' ||
      context.ref !== `refs/heads/${branch}` ||
      env.GITHUB_WORKFLOW_REF !== `${repository.full_name}/.github/workflows/pre-deployment.yml@refs/heads/${branch}` ||
      env.GITHUB_WORKFLOW_SHA !== context.sha) {
    throw new Error('Run the trusted workflow from the protected default branch.');
  }
  const {data: protection} = await github.rest.repos.getBranch({...context.repo, branch});
  if (!protection.protected) {
    throw new Error('Protect the default branch before requesting pre-deployment approval.');
  }
  const {data: pr} = await github.rest.pulls.get({
    ...context.repo, pull_number: Number(input),
  });
  if (pr.state !== 'open' || pr.base.repo.full_name !== repository.full_name ||
      pr.head.repo?.full_name !== repository.full_name || pr.base.ref !== branch ||
      !/^[0-9a-f]{40}$/.test(pr.head.sha)) {
    if (fromPR) return null;
    throw new Error('Select an open same-repository PR into the default branch.');
  }
  if (fromPR) {
    if (context.payload.pull_request?.head?.sha !== pr.head.sha) return null;
    const {data: commit} = await github.rest.repos.getCommit({...context.repo, ref: pr.head.sha});
    if (!commit.commit.message.includes('[digital-twin-test]')) return null;
  }
  return {
    repository: repository.full_name,
    pull_request: pr.number,
    commit: pr.head.sha,
    workflow_commit: env.GITHUB_WORKFLOW_SHA,
    run: env.GITHUB_RUN_ID,
    attempt: env.GITHUB_RUN_ATTEMPT,
  };
};
