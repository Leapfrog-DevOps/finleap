package models

import "time"

type CloudtrailEvent struct {
	EventID     string    `json:"event_id" gorm:"column:eventID;primaryKey"`
	AccountID   string    `json:"account_id" gorm:"column:accountId"`
	EventTime   time.Time `json:"event_time" gorm:"column:eventTime"`
	PrincipalID string    `json:"principal_id" gorm:"column:principalId"`
	Username    string    `json:"username" gorm:"column:username"`
	EventSource string    `json:"event_source" gorm:"column:eventSource"`
	EventName   string    `json:"event_name" gorm:"column:eventName"`
	AwsRegion   string    `json:"aws_region" gorm:"column:awsRegion"`
	ResourceIDs string    `json:"resource_ids" gorm:"column:resourceIds"`
	CreatedAt   time.Time `json:"created_at" gorm:"column:created_at"`
}

func (CloudtrailEvent) TableName() string {
	return "cloudtrail_events"
}

type EC2Cost struct {
	Date         string    `json:"date" gorm:"column:date;primaryKey"`
	InstanceID   string    `json:"instance_id" gorm:"column:instance_id;primaryKey"`
	InstanceType string    `json:"instance_type" gorm:"column:instance_type"`
	CostUSD      float64   `json:"cost_usd" gorm:"column:cost_usd"`
	UsageHours   float64   `json:"usage_hours" gorm:"column:usage_hours"`
	CreatedAt    time.Time `json:"created_at" gorm:"column:created_at"`
	UpdatedAt    time.Time `json:"updated_at" gorm:"column:updated_at"`
}

func (EC2Cost) TableName() string {
	return "ec2_costs"
}

type AccountCost struct {
	AccountID   string  `json:"account_id"`
	TotalCost   float64 `json:"total_cost"`
	TotalHours  float64 `json:"total_hours"`
	Instances   int     `json:"instances"`
}