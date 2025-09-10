package utils

import (
	"context"
	"database/sql"
	_ "github.com/mattn/go-sqlite3"
	"log"
	"strconv"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/costexplorer"
	costexplorerTypes "github.com/aws/aws-sdk-go-v2/service/costexplorer/types"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/aws/aws-sdk-go-v2/service/sts"
)

func NewConfig() aws.Config {
	log.Printf("loading default config for AWS SDK")
	cfg, err := config.LoadDefaultConfig(context.TODO())
	if err != nil {
		log.Fatalf("unable to load SDK config, %v\n", err)
	}
	return cfg
}

func Err(s string, err error) {
	if err != nil {
		log.Fatalf("%s error: %v\n", s, err)
	}
}

func NewS3Client() s3.Client {
	cfg := NewConfig()
	log.Printf("creating new S3 client")
	s3Client := s3.NewFromConfig(cfg)
	return *s3Client
}

func CheckAWSAuth(cfg aws.Config) {
	stsClient := sts.NewFromConfig(cfg)
	authenticated, err := stsClient.GetCallerIdentity(context.TODO(), &sts.GetCallerIdentityInput{})
	if err != nil {
		log.Fatalf("failed to get caller identity, %v\n", err)
	}
	userArn := aws.ToString(authenticated.Arn)
	username := userArn[strings.LastIndex(userArn, "/")+1:]
	log.Println("authenticated as:", username)
}

type CreateEvent struct {
	Username   string
	ResourceId string
	Timestamp  time.Time
}

const SqliteDBPath = "finleap_events.db"

// Initialize SQLite DB and create table if not exists
func InitSqliteDB() (*sql.DB, error) {
	db, err := sql.Open("sqlite3", SqliteDBPath)
	if err != nil {
		return nil, err
	}
	createTable := `CREATE TABLE IF NOT EXISTS events (
	       id INTEGER PRIMARY KEY AUTOINCREMENT,
	       username TEXT,
	       resource_id TEXT,
	       timestamp TEXT
       );`
	_, err = db.Exec(createTable)
	if err != nil {
		return nil, err
	}
	return db, nil
}

// Store a create event in SQLite
func StoreCreateEventSqlite(db *sql.DB, event CreateEvent) error {
	stmt := `INSERT INTO events (username, resource_id, timestamp) VALUES (?, ?, ?)`
	_, err := db.Exec(stmt, event.Username, event.ResourceId, event.Timestamp.Format(time.RFC3339))
	return err
}

// Get all resources created by each user from SQLite
func GetUserResourcesSqlite(db *sql.DB) (map[string][]string, error) {
	result := make(map[string][]string)
	rows, err := db.Query(`SELECT username, resource_id FROM events`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	for rows.Next() {
		var username, resourceId string
		if err := rows.Scan(&username, &resourceId); err != nil {
			continue
		}
		result[username] = append(result[username], resourceId)
	}
	return result, nil
}

// Get cost for a list of resources using Cost Explorer
func GetResourceCosts(cfg aws.Config, resources []string) (map[string]float64, error) {
	ce := costexplorer.NewFromConfig(cfg)
	costs := make(map[string]float64)
	end := time.Now().Format("2006-01-02")
	start := "2023-01-01" // Change as needed
	for _, resource := range resources {
		input := &costexplorer.GetCostAndUsageInput{
			TimePeriod: &costexplorerTypes.DateInterval{
				Start: &start,
				End:   &end,
			},
			Granularity: costexplorerTypes.GranularityMonthly,
			Metrics:     []string{"UnblendedCost"},
			Filter: &costexplorerTypes.Expression{
				Dimensions: &costexplorerTypes.DimensionValues{
					Key:    costexplorerTypes.DimensionResourceId,
					Values: []string{resource},
				},
			},
		}
		resp, err := ce.GetCostAndUsage(context.TODO(), input)
		if err != nil {
			costs[resource] = 0.0
			continue
		}
		var total float64
		for _, res := range resp.ResultsByTime {
			for _, grp := range res.Groups {
				for _, met := range grp.Metrics {
					amt, err := strconv.ParseFloat(*met.Amount, 64)
					if err == nil {
						total += amt
					}
				}
			}
		}
		costs[resource] = total
	}
	return costs, nil
}
