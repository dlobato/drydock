package main

import (
	"bytes"
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"regexp"
	"syscall"
	"time"

	"github.com/actions/scaleset"
)

// shortcut: one disposable job per process, add concurrency only with separate reservation evidence.
func queuedJob(message *scaleset.RunnerScaleSetMessage) (*scaleset.JobMessageBase, bool, error) {
	if message == nil {
		return nil, false, nil
	}
	if message.Statistics != nil && (message.Statistics.TotalAssignedJobs > 1 || message.Statistics.TotalRegisteredRunners > 0) {
		return nil, false, errors.New("the scale set is not an empty single-job reservation")
	}
	var job *scaleset.JobMessageBase
	available := false
	for _, candidate := range message.JobAvailableMessages {
		if job != nil {
			return nil, false, errors.New("multiple queue candidates are refused")
		}
		job, available = &candidate.JobMessageBase, true
	}
	for _, candidate := range message.JobAssignedMessages {
		if job != nil {
			return nil, false, errors.New("multiple queue candidates are refused")
		}
		job = &candidate.JobMessageBase
	}
	if job != nil && message.Statistics == nil {
		return nil, false, errors.New("queue reservation evidence is missing")
	}
	return job, available, nil
}

func dispatch(ctx context.Context, c configuration, state string, token string) (result error) {
	client, err := scaleset.NewClientWithPersonalAccessToken(scaleset.NewClientWithPersonalAccessTokenConfig{
		GitHubConfigURL: "https://github.com/" + repository, PersonalAccessToken: token,
	})
	if err != nil {
		return errors.New("cannot initialize the operator's GitHub client")
	}
	existing, err := client.GetRunnerScaleSet(ctx, 1, "drydock-gke")
	if err != nil || existing != nil {
		return errors.New("inspect the existing scale set before starting this dispatcher")
	}
	labels := make([]scaleset.Label, 0, len(runnerLabels))
	for _, name := range runnerLabels {
		labels = append(labels, scaleset.Label{Name: name})
	}
	set, err := client.CreateRunnerScaleSet(ctx, &scaleset.RunnerScaleSet{
		Name: "drydock-gke", RunnerGroupID: 1, Labels: labels,
		RunnerSetting: scaleset.RunnerSetting{DisableUpdate: true},
	})
	if err != nil {
		return errors.New("cannot create the operator-owned scale set")
	}
	defer func() {
		cleanup, cancel := context.WithTimeout(context.Background(), 90*time.Second)
		defer cancel()
		removed := client.DeleteRunnerScaleSet(cleanup, set.ID) == nil
		if !removed {
			result = errors.Join(result, errors.New("scale-set deletion is incomplete; inspect the operator journal"))
		}
		_ = writeJSON(filepath.Join(state, "outcome.json"), map[string]any{"complete": result == nil, "scale_set_removed": removed})
	}()
	if err := writeJSON(filepath.Join(state, "scale-set.json"), map[string]any{"id": set.ID, "run_id": c.RunID, "run_attempt": c.Attempt}); err != nil {
		return err
	}
	client.SetSystemInfo(scaleset.SystemInfo{System: "drydock", Version: "1", ScaleSetID: set.ID, Subsystem: "listener"})
	session, err := client.MessageSessionClient(ctx, set.ID, filepath.Base(state))
	if err != nil {
		return errors.New("cannot open the GitHub queue session")
	}
	defer func() {
		cleanup, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		if err := session.Close(cleanup); err != nil {
			result = errors.Join(result, errors.New("queue-session deletion failed"))
		}
	}()
	initial := session.Session().Statistics
	if initial == nil || initial.TotalAssignedJobs != 0 || initial.TotalRegisteredRunners != 0 {
		return errors.New("refusing pre-existing reservations or runners")
	}
	fmt.Println("Waiting for one authorized job. No private runner exists.")
	last := 0
	for {
		message, err := session.GetMessage(ctx, last, 1)
		if err != nil {
			return errors.New("GitHub queue polling failed or the dispatcher expired")
		}
		job, available, err := queuedJob(message)
		if err != nil {
			return err
		}
		if job != nil {
			if err := authorize(ctx, c, *job, githubAPI(token)); err != nil {
				_ = writeJSON(filepath.Join(state, "decision.json"), map[string]any{"decision": "denied", "run_id": job.WorkflowRunID, "workflow_ref": job.JobWorkflowRef, "reason": err.Error(), "runner_created": false})
				return err
			}
			if available {
				if job.RunnerRequestID <= 0 {
					return errors.New("available job has no acquisition identity")
				}
				ids, err := session.AcquireJobs(ctx, []int64{job.RunnerRequestID})
				if err != nil || len(ids) != 1 || ids[0] != job.RunnerRequestID {
					return errors.New("the authorized job was not acquired")
				}
			}
			if err := writeJSON(filepath.Join(state, "decision.json"), map[string]any{"decision": "allowed", "run_id": c.RunID, "run_attempt": c.Attempt, "workflow_ref": job.JobWorkflowRef}); err != nil {
				return err
			}
			defer func() {
				cleanup, cancel := context.WithTimeout(context.Background(), 90*time.Second)
				defer cancel()
				runner, err := client.GetRunnerByName(cleanup, filepath.Base(state))
				if err != nil || (runner != nil && (runner.RunnerScaleSetID != set.ID || client.RemoveRunner(cleanup, int64(runner.ID)) != nil)) {
					result = errors.Join(result, errors.New("runner registration deletion is incomplete"))
				}
			}()
			jit, err := client.GenerateJitRunnerConfig(ctx, &scaleset.RunnerScaleSetJitRunnerSetting{Name: filepath.Base(state), WorkFolder: "_work"}, set.ID)
			if err != nil || jit == nil || jit.Runner == nil || jit.EncodedJITConfig == "" {
				return errors.New("cannot register the disposable runner")
			}
			if err := writeJSON(filepath.Join(state, "registration.json"), map[string]any{"runner_id": jit.Runner.ID, "scale_set_id": set.ID}); err != nil {
				return err
			}
			input, _ := json.Marshal(map[string]any{"configuration": c, "jit": jit.EncodedJITConfig, "directory": state})
			return runWithQueue(ctx, session, message.MessageID, job.JobID, func(runContext context.Context) error {
				command := exec.CommandContext(runContext, "python3", "examples/github/runner_vm.py")
				command.Stdin = bytes.NewReader(input)
				command.Stdout, command.Stderr = os.Stdout, os.Stderr
				command.Cancel = func() error { return command.Process.Signal(syscall.SIGTERM) }
				command.WaitDelay = 6 * time.Minute
				if err := command.Run(); err != nil {
					return errors.New("runner execution or disposal failed; inspect the operator journal")
				}
				return nil
			})
		}
		if message != nil {
			last = message.MessageID
			if err := session.DeleteMessage(ctx, message.MessageID); err != nil {
				return errors.New("GitHub queue acknowledgement failed")
			}
		}
	}
}

func writeJSON(path string, value any) error {
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(data, '\n'), 0600)
}

func recoverRunner(ctx context.Context, c configuration, state, token string) error {
	state = filepath.Clean(state)
	if filepath.Dir(state) != filepath.Join("artifacts", "runner-dispatcher") ||
		!regexp.MustCompile(fmt.Sprintf(`^drydock-runner-%d-%d-[a-f0-9]{12}$`, c.RunID, c.Attempt)).MatchString(filepath.Base(state)) {
		return errors.New("recovery requires the selected attempt's operator journal")
	}
	input, _ := json.Marshal(map[string]any{"configuration": c, "directory": state, "recover": true})
	command := exec.CommandContext(ctx, "python3", "examples/github/runner_vm.py")
	command.Stdin = bytes.NewReader(input)
	command.Stdout, command.Stderr = os.Stdout, os.Stderr
	if err := command.Run(); err != nil {
		return errors.New("compute recovery is incomplete; retain the journal and retry")
	}
	var saved struct {
		ID      int   `json:"id"`
		RunID   int64 `json:"run_id"`
		Attempt int   `json:"run_attempt"`
	}
	data, err := os.ReadFile(filepath.Join(state, "scale-set.json"))
	if err != nil || json.Unmarshal(data, &saved) != nil || saved.ID <= 0 || saved.RunID != c.RunID || saved.Attempt != c.Attempt {
		return errors.New("scale-set ownership evidence is missing; inspect GitHub before removal")
	}
	client, err := scaleset.NewClientWithPersonalAccessToken(scaleset.NewClientWithPersonalAccessTokenConfig{
		GitHubConfigURL: "https://github.com/" + repository, PersonalAccessToken: token,
	})
	if err != nil {
		return errors.New("cannot initialize GitHub recovery")
	}
	set, err := client.GetRunnerScaleSet(ctx, 1, "drydock-gke")
	if err != nil || (set != nil && set.ID != saved.ID) {
		return errors.New("scale-set ownership differs or is unavailable; resource preserved")
	}
	runner, err := client.GetRunnerByName(ctx, filepath.Base(state))
	if err != nil || (runner != nil && (runner.RunnerScaleSetID != saved.ID || client.RemoveRunner(ctx, int64(runner.ID)) != nil)) {
		return errors.New("runner registration recovery is incomplete")
	}
	if set != nil {
		if err := client.DeleteRunnerScaleSet(ctx, set.ID); err != nil {
			return errors.New("scale-set recovery is incomplete")
		}
	}
	return writeJSON(filepath.Join(state, "outcome.json"), map[string]any{"recovered": true, "scale_set_removed": true})
}

func main() {
	file := flag.String("configuration", "", "Operator JSON configuration (run from the repository root)")
	recovery := flag.String("recover", "", "Remove only resources owned by an interrupted operator journal")
	flag.Parse()
	data, err := os.ReadFile(*file)
	var c configuration
	if err != nil || json.Unmarshal(data, &c) != nil || c.validate() != nil || os.Getenv("GH_TOKEN") == "" || os.Getenv("CLOUDSDK_CONFIG") == "" {
		fmt.Fprintln(os.Stderr, "Supply a valid operator configuration, GH_TOKEN, and CLOUDSDK_CONFIG.")
		os.Exit(1)
	}
	if *recovery != "" {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
		defer cancel()
		if err := recoverRunner(ctx, c, *recovery, os.Getenv("GH_TOKEN")); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		return
	}
	nonce := make([]byte, 6)
	if _, err := rand.Read(nonce); err != nil {
		panic("cannot generate a dispatcher identity")
	}
	state := filepath.Join("artifacts", "runner-dispatcher", fmt.Sprintf("drydock-runner-%d-%d-%s", c.RunID, c.Attempt, hex.EncodeToString(nonce)))
	if err := os.MkdirAll(state, 0700); err != nil {
		panic("cannot create the operator journal")
	}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	ctx, cancel := context.WithTimeout(ctx, 90*time.Minute)
	defer cancel()
	if err := dispatch(ctx, c, state, os.Getenv("GH_TOKEN")); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println("The one-job dispatcher finished and removed its scale set.")
}
