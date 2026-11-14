package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"slices"
	"time"

	"github.com/actions/scaleset"
)

const repository = "dlobato/drydock"
const workflowPath = ".github/workflows/pre-deployment.yml"
const workflowRef = repository + "/" + workflowPath + "@refs/heads/main"

var runnerLabels = []string{"self-hosted", "linux", "x64", "drydock-gke"}

type configuration struct {
	RunID       int64  `json:"run_id"`
	Attempt     int    `json:"run_attempt"`
	WorkflowSHA string `json:"workflow_sha"`
	Project     string `json:"project"`
	Zone        string `json:"zone"`
	Subnetwork  string `json:"subnetwork"`
	Image       string `json:"image"`
}

func (c configuration) validate() error {
	if c.RunID <= 0 || c.Attempt <= 0 || !regexp.MustCompile(`^[a-f0-9]{40}$`).MatchString(c.WorkflowSHA) {
		return errors.New("set an exact workflow run, attempt, and reviewed main SHA")
	}
	if !regexp.MustCompile(`^[a-z][a-z0-9-]{4,28}[a-z0-9]$`).MatchString(c.Project) ||
		!regexp.MustCompile(`^[a-z]+-[a-z]+[0-9]-[a-z]$`).MatchString(c.Zone) ||
		!regexp.MustCompile(`^[a-z][a-z0-9-]{0,62}$`).MatchString(c.Subnetwork) ||
		!regexp.MustCompile(`^projects/[a-z0-9-]+/global/images/[a-z0-9-]+$`).MatchString(c.Image) {
		return errors.New("set the operator project, zone, subnet, and immutable VM image")
	}
	return nil
}

type apiRead func(context.Context, string, any) error

func githubAPI(token string) apiRead {
	client := &http.Client{Timeout: 20 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error {
		return errors.New("GitHub redirects are refused")
	}}
	return func(ctx context.Context, path string, value any) error {
		request, err := http.NewRequestWithContext(ctx, http.MethodGet, "https://api.github.com/repos/"+repository+"/"+path, nil)
		if err != nil {
			return errors.New("invalid GitHub request")
		}
		request.Header.Set("Authorization", "Bearer "+token)
		request.Header.Set("Accept", "application/vnd.github+json")
		response, err := client.Do(request)
		if err != nil {
			return errors.New("GitHub authorization evidence is unavailable")
		}
		defer response.Body.Close()
		if response.StatusCode != http.StatusOK {
			return fmt.Errorf("GitHub authorization evidence returned HTTP %d", response.StatusCode)
		}
		if err := json.NewDecoder(io.LimitReader(response.Body, 4<<20)).Decode(value); err != nil {
			return errors.New("invalid GitHub authorization evidence")
		}
		return nil
	}
}

func sameLabels(labels []string) bool {
	a, b := slices.Clone(labels), slices.Clone(runnerLabels)
	slices.Sort(a)
	slices.Sort(b)
	return slices.Equal(a, b)
}

func authorize(ctx context.Context, c configuration, job scaleset.JobMessageBase, read apiRead) error {
	if job.OwnerName != "dlobato" || job.RepositoryName != "drydock" || job.JobWorkflowRef != workflowRef ||
		job.WorkflowRunID != c.RunID || job.JobID == "" || !sameLabels(job.RequestLabels) ||
		job.EventName != "workflow_dispatch" {
		return errors.New("queued job is outside the trusted workflow")
	}
	var branch struct {
		Protected bool
		Commit    struct{ SHA string }
	}
	if err := read(ctx, "branches/main", &branch); err != nil {
		return err
	}
	if !branch.Protected || branch.Commit.SHA != c.WorkflowSHA {
		return errors.New("protected main differs from the reviewed workflow revision")
	}
	base := fmt.Sprintf("actions/runs/%d", c.RunID)
	var run struct {
		ID          int64
		RunAttempt  int `json:"run_attempt"`
		Event, Path string
		Status      string
		Repository  struct {
			ID    int64
			Owner struct{ ID int64 }
		}
		HeadRepository struct{ ID int64 } `json:"head_repository"`
	}
	if err := read(ctx, base, &run); err != nil {
		return err
	}
	if run.ID != c.RunID || run.RunAttempt != c.Attempt || run.Event != job.EventName || run.Path != workflowPath ||
		run.Repository.ID != 1452964696 || run.Repository.Owner.ID != 1379455 || run.HeadRepository.ID != 1452964696 ||
		(run.Status != "queued" && run.Status != "in_progress") {
		return errors.New("workflow run or attempt is not eligible for private execution")
	}
	var pending []struct{ Environment struct{ Name string } }
	if err := read(ctx, base+"/pending_deployments", &pending); err != nil {
		return err
	}
	for _, deployment := range pending {
		if deployment.Environment.Name == "gke" {
			return errors.New("gke approval is still pending")
		}
	}
	var reviews []struct {
		State        string
		Environments []struct{ Name string }
	}
	if err := read(ctx, base+"/approvals", &reviews); err != nil {
		return err
	}
	approved := false
	for _, review := range reviews {
		for _, environment := range review.Environments {
			if environment.Name == "gke" {
				if review.State != "approved" {
					return errors.New("the latest gke review did not approve execution")
				}
				approved = true
				break
			}
		}
		if approved {
			break
		}
	}
	if !approved {
		return errors.New("native gke approval evidence is absent")
	}
	var jobs struct {
		Jobs []struct {
			Name, Status string
			RunnerID     int64 `json:"runner_id"`
			Labels       []string
		}
	}
	if err := read(ctx, fmt.Sprintf("%s/attempts/%d/jobs?per_page=100", base, c.Attempt), &jobs); err != nil {
		return err
	}
	matches := 0
	for _, candidate := range jobs.Jobs {
		if sameLabels(candidate.Labels) {
			if candidate.Name != job.JobDisplayName || candidate.Status != "queued" || candidate.RunnerID != 0 {
				return errors.New("the private job differs from the reviewed queued attempt")
			}
			matches++
		}
	}
	if matches != 1 || !regexp.MustCompile(`^Approve (example|scale-100) lab for PR #[1-9][0-9]* at [a-f0-9]{40}$`).MatchString(job.JobDisplayName) {
		return errors.New("exactly one approved lab coordinator is required")
	}
	return nil
}
