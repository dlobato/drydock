package main

import (
	"context"
	"encoding/json"
	"errors"
	"strings"
	"testing"

	"github.com/actions/scaleset"
)

func fixture() (configuration, scaleset.JobMessageBase, map[string]any) {
	c := configuration{RunID: 123, Attempt: 2, WorkflowSHA: strings.Repeat("a", 40)}
	job := scaleset.JobMessageBase{OwnerName: "dlobato", RepositoryName: "drydock", JobWorkflowRef: workflowRef, WorkflowRunID: 123, JobID: "job-guid", EventName: "workflow_dispatch", RequestLabels: runnerLabels, JobDisplayName: "Approve access for PR #21 at aaaaa (no lab)"}
	evidence := map[string]any{
		"branches/main":                                 map[string]any{"protected": true, "commit": map[string]any{"sha": c.WorkflowSHA}},
		"actions/runs/123":                              map[string]any{"id": 123, "run_attempt": 2, "event": "workflow_dispatch", "path": workflowPath, "status": "queued", "repository": map[string]any{"id": 1452964696, "owner": map[string]any{"id": 1379455}}, "head_repository": map[string]any{"id": 1452964696}},
		"actions/runs/123/pending_deployments":          []any{},
		"actions/runs/123/approvals":                    []any{map[string]any{"state": "approved", "environments": []any{map[string]any{"name": "gke"}}}},
		"actions/runs/123/attempts/2/jobs?per_page=100": map[string]any{"jobs": []any{map[string]any{"name": job.JobDisplayName, "status": "queued", "runner_id": 0, "labels": runnerLabels}}},
	}
	return c, job, evidence
}

func evidenceReader(evidence map[string]any) apiRead {
	return func(_ context.Context, path string, value any) error {
		data, ok := evidence[path]
		if !ok {
			return errors.New("evidence unavailable")
		}
		encoded, _ := json.Marshal(data)
		return json.Unmarshal(encoded, value)
	}
}

func TestQueueAuthorizationFailsClosed(t *testing.T) {
	mutations := map[string]func(*configuration, *scaleset.JobMessageBase, map[string]any){
		"valid approved attempt": func(*configuration, *scaleset.JobMessageBase, map[string]any) {},
		"PR-controlled workflow": func(_ *configuration, j *scaleset.JobMessageBase, _ map[string]any) {
			j.JobWorkflowRef = strings.Replace(workflowRef, "main", "attack", 1)
		},
		"missing workflow identity": func(_ *configuration, j *scaleset.JobMessageBase, _ map[string]any) { j.JobWorkflowRef = "" },
		"fork repository":           func(_ *configuration, j *scaleset.JobMessageBase, _ map[string]any) { j.OwnerName = "fork" },
		"different run":             func(_ *configuration, j *scaleset.JobMessageBase, _ map[string]any) { j.WorkflowRunID++ },
		"PR event":                  func(_ *configuration, j *scaleset.JobMessageBase, _ map[string]any) { j.EventName = "pull_request" },
		"unprotected main": func(_ *configuration, _ *scaleset.JobMessageBase, e map[string]any) {
			e["branches/main"].(map[string]any)["protected"] = false
		},
		"changed main": func(_ *configuration, _ *scaleset.JobMessageBase, e map[string]any) {
			e["branches/main"].(map[string]any)["commit"] = map[string]any{"sha": strings.Repeat("b", 40)}
		},
		"stale attempt": func(_ *configuration, _ *scaleset.JobMessageBase, e map[string]any) {
			e["actions/runs/123"].(map[string]any)["run_attempt"] = 3
		},
		"canceled run": func(_ *configuration, _ *scaleset.JobMessageBase, e map[string]any) {
			e["actions/runs/123"].(map[string]any)["status"] = "completed"
		},
		"absent approval": func(_ *configuration, _ *scaleset.JobMessageBase, e map[string]any) {
			e["actions/runs/123/approvals"] = []any{}
		},
		"rejected approval": func(_ *configuration, _ *scaleset.JobMessageBase, e map[string]any) {
			e["actions/runs/123/approvals"].([]any)[0].(map[string]any)["state"] = "rejected"
		},
		"pending approval": func(_ *configuration, _ *scaleset.JobMessageBase, e map[string]any) {
			e["actions/runs/123/pending_deployments"] = []any{map[string]any{"environment": map[string]any{"name": "gke"}}}
		},
		"missing API evidence": func(_ *configuration, _ *scaleset.JobMessageBase, e map[string]any) {
			delete(e, "actions/runs/123/approvals")
		},
		"job absent from attempt": func(_ *configuration, _ *scaleset.JobMessageBase, e map[string]any) {
			e["actions/runs/123/attempts/2/jobs?per_page=100"] = map[string]any{"jobs": []any{}}
		},
	}
	for name, mutate := range mutations {
		t.Run(name, func(t *testing.T) {
			c, job, e := fixture()
			mutate(&c, &job, e)
			err := authorize(context.Background(), c, job, evidenceReader(e))
			if (err == nil) != (name == "valid approved attempt") {
				t.Fatalf("authorization result: %v", err)
			}
		})
	}
}

func TestNativeAssignedJobDoesNotRequireRequestID(t *testing.T) {
	_, job, _ := fixture()
	message := &scaleset.RunnerScaleSetMessage{Statistics: &scaleset.RunnerScaleSetStatistic{TotalAssignedJobs: 1}, JobAssignedMessages: []*scaleset.JobAssigned{{JobMessageBase: job}}}
	selected, available, err := queuedJob(message)
	if err != nil || selected == nil || available || selected.RunnerRequestID != 0 {
		t.Fatal("native routing must still reach authorization before runner registration")
	}
	message.Statistics.TotalAssignedJobs = 2
	if _, _, err := queuedJob(message); err == nil {
		t.Fatal("multiple reservations must prevent private capacity")
	}
	message.Statistics.TotalAssignedJobs = 1
	message.JobAssignedMessages = append(message.JobAssignedMessages, &scaleset.JobAssigned{JobMessageBase: job})
	if _, _, err := queuedJob(message); err == nil {
		t.Fatal("ambiguous job batches must prevent private capacity")
	}
	message.JobAssignedMessages = message.JobAssignedMessages[:1]
	message.Statistics = nil
	if _, _, err := queuedJob(message); err == nil {
		t.Fatal("missing reservation evidence must prevent private capacity")
	}
}
