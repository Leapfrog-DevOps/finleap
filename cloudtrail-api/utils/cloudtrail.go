package utils

import (
	"context"
	"encoding/json"
	"log"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/cloudtrail"
	"github.com/aws/aws-sdk-go-v2/service/cloudtrail/types"
)

func LookupCloudTrailEvents(c cloudtrail.Client, eventNames []string) []types.Event {
	errCount := 0
	var events []types.Event

	for _, eventName := range eventNames {
		input := &cloudtrail.LookupEventsInput{
			StartTime: aws.Time(time.Now().AddDate(0, -12, 0)),
			EndTime:   aws.Time(time.Now()),
			LookupAttributes: []types.LookupAttribute{
				{
					AttributeKey:   types.LookupAttributeKeyEventName,
					AttributeValue: aws.String(eventName),
				},
			},
		}

		output, err := c.LookupEvents(context.TODO(), input)
		if err != nil {
			log.Printf("error looking up events for %s: %v", eventName, err)
			continue
		}

		if len(output.Events) == 0 {
			log.Printf("no events found for %s", eventName)
			continue
		}

		for _, fevt := range output.Events {
			var errorEvent map[string]any
			if err := json.Unmarshal([]byte(aws.ToString(fevt.CloudTrailEvent)), &errorEvent); err != nil {
				log.Printf("failed to unmarshal CloudTrailEvent for %s: %v", aws.ToString(fevt.EventName), err)
				continue
			}

			code, codeOk := errorEvent["errorCode"]
			msg, msgOk := errorEvent["errorMessage"]
			if codeOk || msgOk {
				errCount++
				log.Printf("event name: %s, err code: %v, err msg: %v", aws.ToString(fevt.EventName), code, msg)
				continue
			}
			events = append(events, fevt)
		}
	}

	log.Printf("total events found: %d, total errors found: %d", len(events), errCount)
	return events
}
