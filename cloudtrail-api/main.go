package main

import (
	"context"
	"encoding/json"
	"fmt"
	"finleap/utils"
	"strings"

	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/cloudtrail"
	_ "github.com/aws/aws-sdk-go-v2/service/ec2"
)

func main() {
	cfg, err := config.LoadDefaultConfig(context.TODO())
	utils.Err("error loading default config: %v", err)

	client := *cloudtrail.NewFromConfig(cfg)

	evts := utils.LookupCloudTrailEvents(client, events)

	db, err := utils.InitSqliteDB()
	utils.Err("error initializing sqlite db: %v", err)
	for _, evt := range evts {
		username := "unknown"
		resourceId := "unknown"
		// Get username from evt.Username if present
		if evt.Username != nil && *evt.Username != "" {
			username = *evt.Username
		} else {
			// Fallback: try to parse from CloudTrailEvent
			var eventDetail map[string]any
			if err := json.Unmarshal([]byte(*evt.CloudTrailEvent), &eventDetail); err == nil {
				if v, ok := eventDetail["userIdentity"].(map[string]any); ok {
					if name, ok := v["userName"].(string); ok {
						username = name
					} else if principalId, ok := v["principalId"].(string); ok {
						// Try to extract email from principalId
						parts := strings.Split(principalId, ":")
						if len(parts) > 1 {
							username = parts[1]
						}
					}
				}
			}
		}

		// Get resource from evt.Resources if present
		if len(evt.Resources) > 0 && evt.Resources[0].ResourceName != nil && *evt.Resources[0].ResourceName != "" {
			resourceId = *evt.Resources[0].ResourceName
		} else {
			// Fallback: try to parse from CloudTrailEvent
			var eventDetail map[string]any
			if err := json.Unmarshal([]byte(*evt.CloudTrailEvent), &eventDetail); err == nil {
				// S3: bucketName in requestParameters
				if reqParams, ok := eventDetail["requestParameters"].(map[string]any); ok {
					if bucket, ok := reqParams["bucketName"].(string); ok && bucket != "" {
						resourceId = bucket
					}
				}
			}
		}

		timestamp := evt.EventTime
		event := utils.CreateEvent{
			Username:   username,
			ResourceId: resourceId,
			Timestamp:  *timestamp,
		}
		_ = utils.StoreCreateEventSqlite(db, event)
	}
}

var events = []string{
	// S3
	"CreateBucket",
	"PutBucketReplication",

	// EC2
	"RunInstances",
	"StartInstances",
	"CreateImage",
	"CreateSnapshot",
	"CreateSnapshots",
	"CreateInternetGateway",
	"CreateFlowLogs",
	"CreateFleet",
	"RequestSpotFleet",
	"RequestSpotInstances",
	"CreateNatGateway",
	"CreateStoreImageTask",

	// EBS
	"CreateVolume",
	"CreateSnapshot",
	"CreateSnapshots",
	"RestoreSnapshotTier",
	"CopySnapshot",
	"CopyFpgaImage",

	// VPN
	"CreateClientVpnEndpoint",
}
