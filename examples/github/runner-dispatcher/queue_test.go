package main

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/actions/scaleset"
)

type fakeQueue struct {
	get    func(context.Context, int, int) (*scaleset.RunnerScaleSetMessage, error)
	delete func(context.Context, int) error
}

func (q fakeQueue) GetMessage(ctx context.Context, last, capacity int) (*scaleset.RunnerScaleSetMessage, error) {
	return q.get(ctx, last, capacity)
}

func (q fakeQueue) DeleteMessage(ctx context.Context, id int) error { return q.delete(ctx, id) }

func TestQueueContinuesWhileRunnerBlocks(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	initialAck, started, nextAck := make(chan struct{}), make(chan struct{}), make(chan struct{})
	queue := fakeQueue{
		get: func(ctx context.Context, last, capacity int) (*scaleset.RunnerScaleSetMessage, error) {
			if capacity != 1 {
				t.Error("queue capacity must remain one")
			}
			if last == 1 {
				<-started
				return &scaleset.RunnerScaleSetMessage{MessageID: 2, Statistics: &scaleset.RunnerScaleSetStatistic{TotalAssignedJobs: 1, TotalRegisteredRunners: 1}, JobStartedMessages: []*scaleset.JobStarted{{JobMessageBase: scaleset.JobMessageBase{JobID: "approved"}}}}, nil
			}
			<-ctx.Done()
			return nil, ctx.Err()
		},
		delete: func(_ context.Context, id int) error {
			if id == 1 {
				close(initialAck)
			} else if id == 2 {
				close(nextAck)
			} else {
				t.Errorf("unexpected acknowledgement: %d", id)
			}
			return nil
		},
	}
	err := runWithQueue(ctx, queue, 1, "approved", func(ctx context.Context) error {
		select {
		case <-initialAck:
		default:
			t.Error("runner started before the queue acknowledgement")
		}
		close(started)
		select {
		case <-nextAck:
			return nil
		case <-ctx.Done():
			return ctx.Err()
		}
	})
	if err != nil {
		t.Fatal(err)
	}
}

func TestActiveQueueFailureWaitsForRunnerDisposal(t *testing.T) {
	for _, failure := range []string{"poll", "ack", "missing statistics", "extra runner", "extra reservation", "unexpected available", "unexpected assigned", "unexpected started", "unexpected completed"} {
		t.Run(failure, func(t *testing.T) {
			ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
			defer cancel()
			disposed := make(chan struct{})
			queue := fakeQueue{
				get: func(context.Context, int, int) (*scaleset.RunnerScaleSetMessage, error) {
					m := &scaleset.RunnerScaleSetMessage{MessageID: 2, Statistics: &scaleset.RunnerScaleSetStatistic{TotalAssignedJobs: 1, TotalRegisteredRunners: 1}}
					other := scaleset.JobMessageBase{JobID: "other"}
					switch failure {
					case "poll":
						return nil, errors.New("offline")
					case "missing statistics":
						m.Statistics = nil
					case "extra runner":
						m.Statistics.TotalRegisteredRunners = 2
					case "extra reservation":
						m.Statistics.TotalAssignedJobs = 2
					case "unexpected available":
						m.JobAvailableMessages = []*scaleset.JobAvailable{{JobMessageBase: other}}
					case "unexpected assigned":
						m.JobAssignedMessages = []*scaleset.JobAssigned{{JobMessageBase: other}}
					case "unexpected started":
						m.JobStartedMessages = []*scaleset.JobStarted{{JobMessageBase: other}}
					case "unexpected completed":
						m.JobCompletedMessages = []*scaleset.JobCompleted{{JobMessageBase: other}}
					}
					return m, nil
				},
				delete: func(_ context.Context, id int) error {
					if id == 2 {
						return errors.New("ack failed")
					}
					return nil
				},
			}
			err := runWithQueue(ctx, queue, 1, "approved", func(ctx context.Context) error {
				<-ctx.Done()
				close(disposed)
				return errors.New("runner interrupted")
			})
			if err == nil {
				t.Fatal("queue failure must fail dispatch")
			}
			select {
			case <-disposed:
			default:
				t.Fatal("dispatcher returned before runner disposal")
			}
		})
	}
}

func TestInitialAcknowledgementFailurePreventsRunner(t *testing.T) {
	queue := fakeQueue{delete: func(context.Context, int) error { return errors.New("offline") }}
	if err := runWithQueue(context.Background(), queue, 1, "approved", func(context.Context) error {
		t.Fatal("runner must not start after acknowledgement failure")
		return nil
	}); err == nil {
		t.Fatal("acknowledgement failure must fail dispatch")
	}
}
