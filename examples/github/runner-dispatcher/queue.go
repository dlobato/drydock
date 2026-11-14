package main

import (
	"context"
	"errors"

	"github.com/actions/scaleset"
)

type messageQueue interface {
	GetMessage(context.Context, int, int) (*scaleset.RunnerScaleSetMessage, error)
	DeleteMessage(context.Context, int) error
}

func watchQueue(ctx context.Context, queue messageQueue, last int, jobID string) error {
	for {
		message, err := queue.GetMessage(ctx, last, 1)
		if err != nil {
			if ctx.Err() != nil {
				return ctx.Err()
			}
			return errors.New("GitHub queue polling failed during runner execution")
		}
		if message == nil {
			continue
		}
		stats := message.Statistics
		if stats == nil || stats.TotalAssignedJobs > 1 || stats.TotalRegisteredRunners > 1 {
			return errors.New("the active scale set exceeds the single-job reservation")
		}
		ids := make([]string, 0)
		for _, job := range message.JobAvailableMessages {
			ids = append(ids, job.JobID)
		}
		for _, job := range message.JobAssignedMessages {
			ids = append(ids, job.JobID)
		}
		for _, job := range message.JobStartedMessages {
			ids = append(ids, job.JobID)
		}
		for _, job := range message.JobCompletedMessages {
			ids = append(ids, job.JobID)
		}
		for _, id := range ids {
			if id == "" || id != jobID {
				return errors.New("the active queue contains an unexpected job")
			}
		}
		if err := queue.DeleteMessage(ctx, message.MessageID); err != nil {
			return errors.New("GitHub queue acknowledgement failed during runner execution")
		}
		last = message.MessageID
	}
}

func runWithQueue(ctx context.Context, queue messageQueue, messageID int, jobID string, run func(context.Context) error) error {
	// Keep the reservation alive while VM preparation and execution block.
	if err := queue.DeleteMessage(ctx, messageID); err != nil {
		return errors.New("GitHub queue acknowledgement failed before runner creation")
	}
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	runnerDone, queueDone := make(chan error, 1), make(chan error, 1)
	go func() { runnerDone <- run(ctx) }()
	go func() { queueDone <- watchQueue(ctx, queue, messageID, jobID) }()
	select {
	case err := <-runnerDone:
		cancel()
		if queueError := <-queueDone; !errors.Is(queueError, context.Canceled) {
			err = errors.Join(err, queueError)
		}
		return err
	case err := <-queueDone:
		cancel()
		return errors.Join(err, <-runnerDone)
	}
}
