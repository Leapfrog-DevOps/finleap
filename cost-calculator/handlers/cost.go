package handlers

import (
	"cost-calculator/database"
	"cost-calculator/models"
	"net/http"

	"github.com/gin-gonic/gin"
)

func GetPrincipalCosts(c *gin.Context) {
	var costs []struct {
		PrincipalID string `json:"principal_id"`
		ResourceIDs string `json:"resource_ids"`
	}
	
	query := `
		SELECT DISTINCT
			ce.principalId as principal_id,
			ce.resourceIds as resource_ids
		FROM cloudtrail_events ce
		WHERE ce.principalId IS NOT NULL 
			AND ce.principalId != ''
			AND ce.resourceIds IS NOT NULL
			AND ce.resourceIds != ''
		ORDER BY ce.principalId
	`
	
	if err := database.GetDB().Raw(query).Scan(&costs).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	
	c.JSON(http.StatusOK, costs)
}

func GetPrincipalCostByID(c *gin.Context) {
	principalID := c.Param("id")
	
	if principalID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Principal ID is required"})
		return
	}
	
	var exists bool
	if err := database.GetDB().Raw("SELECT EXISTS(SELECT 1 FROM cloudtrail_events WHERE principalId = ?)", principalID).Scan(&exists).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	
	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "Principal ID not found"})
		return
	}
	
	var cost struct {
		PrincipalID string `json:"principal_id"`
		TotalCost   float64 `json:"total_cost"`
		TotalHours  float64 `json:"total_hours"`
		InstanceIDs string `json:"instance_ids"`
		CreatedAt   string `json:"created_at"`
	}
	
	query := `
		SELECT 
			ce.principalId as principal_id,
			COALESCE(SUM(ec.cost_usd), 0) as total_cost,
			COALESCE(SUM(ec.usage_hours), 0) as total_hours,
			GROUP_CONCAT(DISTINCT ec.instance_id) as instance_ids,
			MIN(ce.created_at) as created_at
		FROM cloudtrail_events ce
		LEFT JOIN ec2_costs ec ON JSON_CONTAINS(ce.resourceIds, CONCAT('"', ec.instance_id, '"'))
		WHERE ce.principalId = ?
		GROUP BY ce.principalId
	`
	
	if err := database.GetDB().Raw(query, principalID).Scan(&cost).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	
	if cost.PrincipalID == "" {
		c.JSON(http.StatusNotFound, gin.H{"error": "Principal not found"})
		return
	}
	
	c.JSON(http.StatusOK, cost)
}

func GetPrincipalResourceMapping(c *gin.Context) {
	var results []struct {
		PrincipalID string `json:"principal_id"`
		ResourceIDs string `json:"resource_ids"`
	}
	
	query := `
		SELECT DISTINCT
			ce.principalId as principal_id,
			ce.resourceIds as resource_ids
		FROM cloudtrail_events ce
		WHERE ce.principalId IS NOT NULL 
			AND ce.principalId != ''
			AND ce.resourceIds IS NOT NULL
			AND ce.resourceIds != ''
		ORDER BY ce.principalId
	`
	
	if err := database.GetDB().Raw(query).Scan(&results).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	
	c.JSON(http.StatusOK, results)
}

func GetInstanceCosts(c *gin.Context) {
	var costs []models.EC2Cost
	
	if err := database.GetDB().Find(&costs).Error; err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	
	c.JSON(http.StatusOK, costs)
}