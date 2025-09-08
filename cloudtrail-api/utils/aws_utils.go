package utils

import (
	"context"
	"log"
	"strings"
	"time"

	_ "github.com/mattn/go-sqlite3"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
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
