package utils

import "github.com/aws/aws-sdk-go-v2/aws"

// Get cost for a list of resources using Cost Explorer
func GetResourceCosts(cfg aws.Config, resources []string) (map[string]float64, error) {
	// TODO: discuss whether this should be the part of this or not
	panic("not implemented")
}
